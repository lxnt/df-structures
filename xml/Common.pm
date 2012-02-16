package Common;

use utf8;
use strict;
use warnings;

BEGIN {
    use Exporter  ();
    our $VERSION = 1.00;
    our @ISA     = qw(Exporter);
    our @EXPORT  = qw(
        $main_namespace $export_prefix
        %types %type_files %globals %global_files *typename *filename

        &parse_address &check_bad_attrs &check_name
        &is_attr_true &type_header_def &add_type_to_hash &add_global_to_hash

        *lines *indentation &with_emit &emit &indent &outdent &emit_block

        &is_primitive_type &primitive_type_name &get_primitive_base

        *weak_refs *strong_refs &register_ref &decode_type_name_ref

        *cur_header_name %header_data &with_header_file

        %static_lines %static_includes &with_emit_static

        &ensure_name &with_anon

        &fully_qualified_name
        &get_comment &emit_comment
    );
    our %EXPORT_TAGS = ( ); # eg: TAG => [ qw!name1 name2! ],
    our @EXPORT_OK   = qw( );
}

END { }

use XML::LibXML;

our $main_namespace = '';
our $export_prefix = '';

our %types;
our %type_files;

our %globals;
our %global_files;

# Misc XML analysis

our $typename;
our $filename;

sub parse_address($;$) {
    my ($str,$in_bits) = @_;
    return undef unless defined $str;
    
    # Parse the format used by offset attributes in xml
    $str =~ /^0x([0-9a-f]+)(?:\.([0-7]))?$/
        or die "Invalid address syntax: $str\n";
    my ($full, $bv) = ($1, $2);
    die "Bits not allowed: $str\n" unless $in_bits;
    return $in_bits ? (hex($full)*8 + ($bv||0)) : hex($full);
}

sub check_bad_attrs($;$$) {
    my ($tag, $allow_size, $allow_align) = @_;
    
    die "Cannot use size, alignment or offset for ".$tag->nodeName."\n"
        if ((!$allow_size && defined $tag->getAttribute('size')) ||
            defined $tag->getAttribute('offset') ||
            (!$allow_align && defined $tag->getAttribute('alignment')));
}

sub check_name($) {
    my ($name) = @_;
    $name =~ /^[_a-zA-Z][_a-zA-Z0-9]*$/
        or die "Invalid identifier: $name\n";
    return $name;
}

sub is_attr_true($$) {
    my ($tag, $name) = @_;
    return ($tag->getAttribute($name)||'') eq 'true';
}

sub type_header_def($) {
    my ($name) = @_;
    return uc($main_namespace).'_'.uc($name).'_H';
}

sub add_type_to_hash($) {
    my ($type) = @_;

    my $name = $type->getAttribute('type-name')
        or die "Type without a name in $filename\n";

    die "Duplicate definition of $name in $filename\n" if $types{$name};

    local $typename = $name;
    check_bad_attrs $type;
    $types{$name} = $type;
    $type_files{$name} = $filename;
}

sub add_global_to_hash($) {
    my ($type) = @_;

    my $name = $type->getAttribute('name')
        or die "Global without a name in $filename\n";

    die "Duplicate definition of global $name in $filename\n" if $globals{$name};

    local $typename = $name;
    check_bad_attrs $type;
    $globals{$name} = $type;
    $global_files{$name} = $filename;
}

# Text generation with indentation

our @lines;
our $indentation = 0;

sub with_emit(&;$) { 
    # Executes the code block, and returns emitted lines
    my ($blk, $start_indent) = @_;
    local @lines;
    local $indentation = ($start_indent||0);
    $blk->();
    return @lines;
}

sub emit(@) {
    # Emit an indented line to be returned from with_emit
    my $line = join('',map { defined($_) ? $_ : '' } @_);
    $line = (' 'x$indentation).$line unless length($line) == 0;
    push @lines, $line;
}

sub indent(&) {
    # Indent lines emitted from the block by one step
    my ($blk) = @_;
    local $indentation = $indentation+2;
    $blk->();
}

sub outdent(&) {
    # Unindent lines emitted from the block by one step
    my ($blk) = @_;
    local $indentation = ($indentation >= 2 ? $indentation-2 : 0);
    $blk->();
}

sub emit_block(&;$$%) {
    # Emit a full {...} block with indentation
    my ($blk, $prefix, $suffix, %flags) = @_;
    my @inner = &with_emit($blk,$indentation+2);
    return if $flags{-auto} && !@inner;
    $prefix ||= '';
    $suffix ||= '';
    emit $prefix,'{';
    push @lines, @inner;
    emit '}',$suffix;
}

# Primitive types

my @primitive_type_list =
    qw(int8_t uint8_t int16_t uint16_t
       int32_t uint32_t int64_t uint64_t
       s-float
       bool flag-bit
       padding static-string);

my %primitive_aliases = (
    's-float' => 'float',
    'static-string' => 'char',
    'flag-bit' => 'void',
    'padding' => 'void',
);

my %primitive_types;
$primitive_types{$_}++ for @primitive_type_list;

sub is_primitive_type($) {
    return $primitive_types{$_[0]};
}

sub primitive_type_name($) {
    my ($tag_name) = @_;
    $primitive_types{$tag_name}
        or die "Not primitive: $tag_name\n";
    return $primitive_aliases{$tag_name} || $tag_name;
}

sub get_primitive_base($;$) {
    my ($tag, $default) = @_;

    my $base = $tag->getAttribute('base-type') || $default || 'uint32_t';
    $primitive_types{$base} or die "Must be primitive: $base\n";

    return $base;
}

# Type references

our %weak_refs;
our %strong_refs;

sub register_ref($;$) {
    # Register a reference to another type.
    # Strong ones require the type to be included.
    my ($ref, $is_strong) = @_;

    if ($ref) {
        my $type = $types{$ref}
            or die "Unknown type $ref referenced.\n";

        if ($is_strong) {
            $strong_refs{$ref}++;
        } else {
            $weak_refs{$ref}++;
        }

        return $type;
    } else {
        return undef;
    }
}

sub decode_type_name_ref($;%) {
    # Interpret the type-name field of a tag
    my ($tag,%flags) = @_;
    my $force_type = $flags{-force_type};
    my $attr = $flags{-attr_name} || 'type-name';
    my $tname = $tag->getAttribute($attr) or return undef;

    if ($primitive_types{$tname}) {
        die "Cannot use type $tname as $attr here: $tag\n"
            if ($force_type && $force_type ne 'primitive');
        return primitive_type_name($tname);
    } else {
        register_ref $tname, !$flags{-weak};
        die "Cannot use type $tname as $attr here: $tag\n"
            if ($force_type && $force_type ne $types{$tname}->getAttribute('ld:meta'));
        my $rtype = $main_namespace.'::'.$tname;
        return wantarray ? ($rtype, $types{$tname}) : $rtype;
    }
}

# Include file generation

our $cur_header_name;
our %header_data;

sub with_header_file(&$) {
    my ($handler, $header_name) = @_;

    local $cur_header_name = $header_name;

    local %weak_refs;
    local %strong_refs;

    # Emit the actual type definition
    my @code = with_emit {
        &with_anon($handler);
    } 2;

    delete $weak_refs{$header_name};
    delete $strong_refs{$header_name};

    # Add wrapping
    my @all = with_emit {
        my $def = type_header_def($header_name);
        emit "#ifndef $def";
        emit "#define $def";

        for my $strong (sort { $a cmp $b } keys %strong_refs) {
            my $sdef = type_header_def($strong);
            emit "#ifndef $sdef";
            emit "#include \"$strong.h\"";
            emit "#endif";
        }

        emit_block {
            for my $weak (sort { $a cmp $b } keys %weak_refs) {
                next if $strong_refs{$weak};
                my $ttype = $types{$weak};
                my $tstr = 'struct';
                $tstr = 'enum' if $ttype->nodeName eq 'enum-type';
                $tstr = 'union' if $ttype->nodeName eq 'bitfield-type';
                $tstr = 'union' if ($ttype->nodeName eq 'struct-type' && is_attr_true($ttype,'is-union'));
                emit $tstr, ' ', $weak, ';';
            }

            push @lines, @code;
        } "namespace $main_namespace ";

        emit "#endif";
    };

    $header_data{$header_name} = \@all;
}

# Static file output

our %static_lines;
our %static_includes;

sub with_emit_static(&;$) {
    my ($blk, $tag) = @_;
    my @inner = &with_emit($blk,2) or return;
    $tag ||= '';
    $static_includes{$tag}{$cur_header_name}++ if $cur_header_name;
    push @{$static_lines{$tag}}, @inner;
}

# Anonymous variable names

our $anon_id = 0;
our $anon_prefix;

sub ensure_name($) {
    # If the name is empty, assign an auto-generated one
    my ($name) = @_;
    unless ($name) {
        $name = $anon_prefix.(($anon_id == 0) ? '' : '_'.$anon_id);
        $anon_id++;
    }
    return check_name($name);
}

sub with_anon(&;$) {
    # Establish a new anonymous namespace
    my ($blk,$stem) = @_;
    local $anon_id = $stem ? 0 : 1;
    local $anon_prefix = ($stem||'anon');
    $blk->();
}

# Global type names

sub fully_qualified_name($$;$) {
    my ($tag, $name, $no_ns) = @_;
    my @names;
    push @names, $main_namespace unless $no_ns;
    for my $parent ($tag->findnodes('ancestor::*')) {
        if ($parent->nodeName eq 'ld:global-type') {
            push @names, $parent->getAttribute('type-name');
        } elsif (my $n = $parent->getAttribute('ld:typedef-name')) {
            push @names, $n;
        }
    }
    return join('::',@names,$name);
}

# Comments

sub get_comment($) {
    my ($tag) = @_;

    return '' unless $tag;

    if (my $val = $tag->getAttribute('comment')) {
        return ' /*!< '.$val.' */';
    } else {
        return '';
    }
}

sub emit_comment($;%) {
    my ($tag,%flags) = @_;

    return unless $tag;

    my $val = $tag->findvalue('child::comment');

    if ($flags{-attr}) {
        my $attr = $tag->getAttribute('comment');
        if ($attr && $val) {
            $val = $attr."\n".$val;
        } else {
            $val ||= $attr;
        }
    }

    if ($val) {
        emit '/**';
        for my $line (split(/\n/, $val)) {
            $line =~ s/^\s*//;
            $line =~ s/\s*$//;
            next if $line eq '';
            emit ' * ', $line;
        }
        emit ' */';
    }
}

1;
