/*
https://github.com/peterix/dfhack
Copyright (c) 2009-2011 Petr Mrázek (peterix@gmail.com)

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any
damages arising from the use of this software.

Permission is granted to anyone to use this software for any
purpose, including commercial applications, and to alter it and
redistribute it freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must
not claim that you wrote the original software. If you use this
software in a product, an acknowledgment in the product documentation
would be appreciated but is not required.

2. Altered source versions must be plainly marked as such, and
must not be misrepresented as being the original software.

3. This notice may not be removed or altered from any source
distribution.
*/

#pragma once

#include <string>
#include <vector>
#include <map>
#include <iostream>

#include "df/api.h"

// Stop some MS stupidity
#ifdef interface
	#undef interface
#endif

namespace df
{
    class virtual_class {};

#ifdef _MSC_VER
    typedef void *virtual_ptr;
#else
    typedef virtual_class *virtual_ptr;
#endif

    class DFAPI_EXPORT virtual_identity {
        static virtual_identity *list;
        static std::map<void*, virtual_identity*> known;
        static df::api::essentials *esse;
        
        virtual_identity *prev, *next;
        const char *dfhack_name;
        const char *original_name;
        virtual_identity *parent;
        std::vector<virtual_identity*> children;
        
        void *vtable_ptr;
        bool has_children;

    protected:
        virtual_identity(const char *dfhack_name, const char *original_name, virtual_identity *parent);

        static void *get_vtable(virtual_ptr instance_ptr) { return *(void**)instance_ptr; }

    public:
        const char *getName() { return dfhack_name; }
        const char *getOriginalName() { return original_name ? original_name : dfhack_name; }

        virtual_identity *getParent() { return parent; }
        const std::vector<virtual_identity*> &getChildren() { return children; }

    public:
        static virtual_identity *get(virtual_ptr instance_ptr);
        
        bool is_subclass(virtual_identity *subtype);
        bool is_instance(virtual_ptr instance_ptr) {
            if (!instance_ptr) return false;
            if (vtable_ptr) {
                void *vtable = get_vtable(instance_ptr);
                if (vtable == vtable_ptr) return true;
                if (!has_children) return false;
            }
            return is_subclass(get(instance_ptr));
        }

        bool is_direct_instance(virtual_ptr instance_ptr) {
            if (!instance_ptr) return false;
            return vtable_ptr ? (vtable_ptr == get_vtable(instance_ptr)) 
                              : (this == get(instance_ptr));
        }

    public:
        bool can_instantiate() { return (vtable_ptr != NULL); }
        virtual_ptr instantiate() { return can_instantiate() ? do_instantiate() : NULL; }
        static virtual_ptr clone(virtual_ptr obj);

    protected:
        virtual virtual_ptr do_instantiate() = 0;
        virtual void do_copy(virtual_ptr tgt, virtual_ptr src) = 0;
    public:
        static DFAPI_EXPORT void Init(df::api::essentials *);

        // Strictly for use in virtual class constructors
        void adjust_vtable(virtual_ptr obj, virtual_identity *main);
    };

    template<class T>
    inline T *virtual_cast(virtual_ptr ptr) {
        return T::_identity.is_instance(ptr) ? static_cast<T*>(ptr) : NULL;
    }

#define VIRTUAL_CAST_VAR(var,type,input) type *var = df::virtual_cast<type>(input)

    template<class T>
    inline T *strict_virtual_cast(virtual_ptr ptr) {
        return T::_identity.is_direct_instance(ptr) ? static_cast<T*>(ptr) : NULL;
    }

#define STRICT_VIRTUAL_CAST_VAR(var,type,input) type *var = df::strict_virtual_cast<type>(input)

    //void InitDataDefGlobals(Core *core);

    template<class T>
    class class_virtual_identity : public virtual_identity {
    public:
        class_virtual_identity(const char *dfhack_name, const char *original_name, virtual_identity *parent)
            : virtual_identity(dfhack_name, original_name, parent) {};

        T *instantiate() { return static_cast<T*>(virtual_identity::instantiate()); }
        T *clone(T* obj) { return static_cast<T*>(virtual_identity::clone(obj)); }

    protected:
        virtual virtual_ptr do_instantiate() { return new T(); }
        virtual void do_copy(virtual_ptr tgt, virtual_ptr src) { *static_cast<T*>(tgt) = *static_cast<T*>(src); }
    };


}

#define ENUM_ATTR(enum,attr,val) (df::enums::enum::get_##attr(val))
#define ENUM_ATTR_STR(enum,attr,val) df::ifnull(ENUM_ATTR(enum,attr,val),"?")
#define ENUM_KEY_STR(enum,val) ENUM_ATTR_STR(enum,key,val)
#define ENUM_FIRST_ITEM(enum) (df::enums::enum::_first_item_of_##enum)
#define ENUM_LAST_ITEM(enum) (df::enums::enum::_last_item_of_##enum)

#define ENUM_NEXT_ITEM(enum,val) \
    (df::next_enum_item_<df::enum,ENUM_FIRST_ITEM(enum),df::enums::enum::is_valid>(val))
#define FOR_ENUM_ITEMS(enum,iter) \
    for(df::enum iter = ENUM_FIRST_ITEM(enum); iter <= ENUM_LAST_ITEM(enum); iter = df::enum(1+int(iter)))

// Global object pointers
#include "df/global_objects.h"


