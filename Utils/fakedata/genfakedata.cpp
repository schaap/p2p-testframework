#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>

#include "fakedata.h"

#ifdef _WIN32
#define OPENFLAGS         O_RDWR|O_CREAT|_O_BINARY
#else
#define OPENFLAGS         O_RDWR|O_CREAT
#endif

int main( int argc, char** argv ) {
    if( argc < 3 ) {
        printf( "Usage: %s outputfile size\n", argv[0] );
        printf( "Prints semi-non-trivial data to a file: at each 4th byte (0, 3, 7, ...) it prints a 32-bit counter (0, 1, 2, ...) in big-endian byte order\n" );
        printf( "- outputfile : the file to write to\n" );
        printf( "- size : the desired size of the file (will be rounded up to a multiple of 4)\n" );
        return -1;
    }

    size_t n = strtol( argv[2], NULL, 10 );
    if( n < 1 ) {
        printf( "Positive size in bytes expected, got %s\n", argv[2] );
        return -1;
    }
    if( n & 0x3 ) {
        n = ( n & ~0X3 ) + 4;
        printf( "Warning: size was given as %s, which is not a multiple of 4. %li bytes will be written instead.\n", argv[2], (long int) n );
    }
    if( n > (long long int)16 * 1024 * 1024 * 1024 ) {
        printf( "Fake data counter is 32 bits, meaning it can count to 4G and, printing 4 bytes for each count, can generate a maximum file size of 16G\n" );
        return -1;
    }

    int f = open( argv[1], OPENFLAGS, S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH );
    if( f < 0 ) {
        perror( argv[1] );
        return -1;
    }

    return generateFakeData( f, n );
}
