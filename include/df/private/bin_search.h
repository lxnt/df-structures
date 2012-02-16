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
#include <iostream>
#include <iomanip>
#include <climits>
#include <stdint.h>
#include <vector>
#include <sstream>
#include <cstdio>
#include "df/private/export.h"

using namespace std;

/*
 * Binary search in vectors.
 */

template <typename FT>
int linear_index(const std::vector<FT> &vec, FT key)
{
    for (unsigned i = 0; i < vec.size(); i++)
        if (vec[i] == key)
            return i;
    return -1;
}

template <typename FT>
int linear_index(const std::vector<FT*> &vec, const FT &key)
{
    for (unsigned i = 0; i < vec.size(); i++)
        if (vec[i] && *vec[i] == key)
            return i;
    return -1;
}

template <typename FT>
int binsearch_index(const std::vector<FT> &vec, FT key, bool exact = true)
{
    // Returns the index of the value >= the key
    int min = -1, max = (int)vec.size();
    const FT *p = vec.data();
    for (;;)
    {
        int mid = (min + max)>>1;
        if (mid == min)
            return exact ? -1 : max;
        FT midv = p[mid];
        if (midv == key)
            return mid;
        else if (midv < key)
            min = mid;
        else
            max = mid;
    }
}

template <typename CT, typename FT>
int linear_index(const std::vector<CT*> &vec, FT CT::*field, FT key)
{
    for (unsigned i = 0; i < vec.size(); i++)
        if (vec[i]->*field == key)
            return i;
    return -1;
}

template <typename CT, typename FT>
int binsearch_index(const std::vector<CT*> &vec, FT CT::*field, FT key, bool exact = true)
{
    // Returns the index of the value >= the key
    int min = -1, max = (int)vec.size();
    CT *const *p = vec.data();
    for (;;)
    {
        int mid = (min + max)>>1;
        if (mid == min)
            return exact ? -1 : max;
        FT midv = p[mid]->*field;
        if (midv == key)
            return mid;
        else if (midv < key)
            min = mid;
        else
            max = mid;
    }
}

template <typename CT>
inline int binsearch_index(const std::vector<CT*> &vec, typename CT::key_field_type key, bool exact = true)
{
    return CT::binsearch_index(vec, key, exact);
}

template <typename CT>
inline int binsearch_index(const std::vector<CT*> &vec, typename CT::key_pointer_type key, bool exact = true)
{
    return CT::binsearch_index(vec, key, exact);
}

template<typename FT, typename KT>
inline bool vector_contains(const std::vector<FT> &vec, KT key)
{
    return binsearch_index(vec, key) >= 0;
}

template<typename CT, typename FT>
inline bool vector_contains(const std::vector<CT*> &vec, FT CT::*field, FT key)
{
    return binsearch_index(vec, field, key) >= 0;
}

template<typename T>
inline T vector_get(const std::vector<T> &vec, unsigned idx, const T &defval = T())
{
    if (idx < vec.size())
        return vec[idx];
    else
        return defval;
}

template<typename T>
inline void vector_insert_at(std::vector<T> &vec, unsigned idx, const T &val)
{
    vec.insert(vec.begin()+idx, val);
}

template<typename T>
inline void vector_erase_at(std::vector<T> &vec, unsigned idx)
{
    if (idx < vec.size())
        vec.erase(vec.begin()+idx);
}

template<typename FT>
unsigned insert_into_vector(std::vector<FT> &vec, FT key, bool *inserted = NULL)
{
    unsigned pos = (unsigned)binsearch_index(vec, key, false);
    bool to_ins = (pos >= vec.size() || vec[pos] != key);
    if (inserted) *inserted = to_ins;
    if (to_ins)
        vector_insert_at(vec, pos, key);
    return pos;
}

template<typename CT, typename FT>
unsigned insert_into_vector(std::vector<CT*> &vec, FT CT::*field, CT *obj, bool *inserted = NULL)
{
    unsigned pos = (unsigned)binsearch_index(vec, field, obj->*field, false);
    bool to_ins = (pos >= vec.size() || vec[pos] != obj);
    if (inserted) *inserted = to_ins;
    if (to_ins)
        vector_insert_at(vec, pos, obj);
    return pos;
}

template <typename CT, typename KT>
CT *binsearch_in_vector(const std::vector<CT*> &vec, KT value)
{
    int idx = binsearch_index(vec, value);
    return idx < 0 ? NULL : vec[idx];
}

template <typename CT, typename FT>
CT *binsearch_in_vector(const std::vector<CT*> &vec, FT CT::*field, FT value)
{
    int idx = binsearch_index(vec, field, value);
    return idx < 0 ? NULL : vec[idx];
}
