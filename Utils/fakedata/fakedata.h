#ifndef FAKEDATA_H
#define FAKEDATA_H

#include <sys/types.h>

#include "compat.h"

/**
 * Generates a fake data file in the file pointed to by f of size n bytes.
 *
 * @param   f       The fileno of the file to write.
 * @param   n       The exact number of bytes that will be written to f. Should be a multiple of 4 and no greater than 2^32.
 *
 * @return  0 for succes, non-0 otherwise.
 */
int generateFakeData( int filename, size_t n);

#define file_resize( f, n ) ftruncate( f, n )

void file_size( int f );

#endif
