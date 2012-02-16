#include "df/api.h"
#include "df/global_objects.h"
#include "df/private/virtual_identity.h"
#include "df/private/bin_search.h"
#include "df/private/bit_array.h"

namespace {
    template<class T>
    inline T &_toref(T &r) { return r; }
    template<class T>
    inline T &_toref(T *&p) { return *p; }
}

namespace df {
    std::string bitfieldToString(const void *p, int size, const bitfield_item_info *items)
    {
        std::string res;
        const char *data = (const char*)p;
        char buf_[32];
        
        for (int i = 0; i < size*8; i++) {
            unsigned v;

            if (items[i].size > 1) {
                unsigned pdv = *(unsigned*)&data[i/8];
                v = (pdv >> (i%8)) & ((1 << items[i].size)-1);
            } else {
                v = (data[i/8]>>(i%8)) & 1;
            }

            if (v) {
                if (!res.empty())
                    res += ' ';

                if (items[i].name)
                    res += items[i].name;
                else
                    snprintf(buf_, 32, "UNK_%d", i), res += buf_;

                if (items[i].size > 1)
            snprintf(buf_, 32, "=%u", v), res += buf_;
            }

            if (items[i].size > 1)
                i += items[i].size-1;
        }

        return res;
    }

    int findBitfieldField(const std::string &name, int size, const bitfield_item_info *items)
    {
        for (int i = 0; i < size*8; i++) {
            if (items[i].name && items[i].name == name)
                return i;
        }

        return -1;
    }
}

// Object constructors
#include "df/static.ctors.inc"

// Instantiate all the static objects
#include "df/static.inc"
#include "df/static.enums.inc"
