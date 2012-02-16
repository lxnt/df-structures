#!/usr/bin/perl

use strict;
use warnings;

use XML::LibXML;

my $input_dir = $ARGV[0] || '.';
my $output_dir = $ARGV[1] || 'codegen';
my $separator = $ARGV[2] || "\n";

my @list;

push @list, "$output_dir/codegen.out.xml";
push @list, "$output_dir/global_objects.h";
push @list, "$output_dir/static.enums.inc";
push @list, "$output_dir/static.ctors.inc";
push @list, "$output_dir/static.inc";

for my $filename (glob "$input_dir/*.xml") {
    my $parser = XML::LibXML->new();
    my $doc    = $parser->parse_file($filename);

    my @nodes = (
        $doc->findnodes('/data-definition/enum-type'),
        $doc->findnodes('/data-definition/bitfield-type'),
        $doc->findnodes('/data-definition/struct-type'),
        $doc->findnodes('/data-definition/class-type')
    );

    for my $node (@nodes) {
        my $name = $node->getAttribute('type-name')
            or die "Unnamed type in $filename\n";
        push @list, "$output_dir/$name.h";
    }
}

if ($separator eq "--delete") {
    for my $item (@list) {
        unlink $item;
    }
} else {
    print join( $separator, @list );
    print $separator if $separator eq "\n";
}

