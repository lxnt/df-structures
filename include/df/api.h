/* THIS FILE WAS NOT GENERATED. DO EDIT. */
#ifndef DF_API_H
#define DF_API_H

#include <map>
#include <string>
#include <vector>

#include "df/private/export.h"

namespace df {
    template<class T>
    T *ifnull(T *a, T *b) { return a ? a : b; }

    // Enums
    template<class T, T start, bool (*isvalid)(T)>
    inline T next_enum_item_(T v) {
        v = T(int(v) + 1);
        return isvalid(v) ? v : start;
    }

    template<class T>
    struct enum_list_attr {
        int size;
        const T *items;
    };

    // Bitfields
    struct bitfield_item_info {
        const char *name;
        int size;
    };

    DFAPI_EXPORT std::string bitfieldToString(const void *p, int size, const bitfield_item_info *items);
    DFAPI_EXPORT int findBitfieldField(const std::string &name, int size, const bitfield_item_info *items);

    template<class T>
    inline int findBitfieldField(const T &val, const std::string &name) {
        return findBitfieldField(name, sizeof(val.whole), val.get_items());
    }

    template<class T>
    inline std::string bitfieldToString(const T &val) {
        return bitfieldToString(&val.whole, sizeof(val.whole), val.get_items());
    }    
    template<class EnumType, class IntType = int32_t>
    struct enum_field {
        IntType value;

        enum_field() {}
        enum_field(EnumType ev) : value(IntType(ev)) {}
        template<class T>
        enum_field(enum_field<EnumType,T> ev) : value(IntType(ev.value)) {}

        operator EnumType () { return EnumType(value); }
        enum_field<EnumType,IntType> &operator=(EnumType ev) {
            value = IntType(ev); return *this;
        }
    };

    template<class EnumType, class IntType1, class IntType2>
    inline bool operator== (enum_field<EnumType,IntType1> a, enum_field<EnumType,IntType2> b)
    {
        return EnumType(a) == EnumType(b);
    }

    template<class EnumType, class IntType1, class IntType2>
    inline bool operator!= (enum_field<EnumType,IntType1> a, enum_field<EnumType,IntType2> b)
    {
        return EnumType(a) != EnumType(b);
    }

    namespace enums {}
	
    namespace api {
	class essentials {
	public:
	    virtual std::string readClassName(void *) = 0;
	    virtual void lock() = 0;
	    virtual void unlock() = 0;
	    virtual std::map<std::string, void *>& getVtable() = 0;
	    virtual void *getGlobal(const char *name) = 0; 
	};
    }	
}
#define INIT_GLOBAL_FUNCTION_PARAMETERS df::api::essentials* esse
#define INIT_GLOBAL_FUNCTION_PREFIX df::virtual_identity::Init(esse);
#define INIT_GLOBAL_FUNCTION_ITEM(type,name) name = (type *) esse->getGlobal(#name);

// A couple of headers that have to be included at once
#include "df/private/bit_array.h"
#include "df/private/bin_search.h"
#include "df/private/virtual_identity.h"
#include "df/coord2d.h"
#include "df/coord.h"


#endif