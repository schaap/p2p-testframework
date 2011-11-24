#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdint.h>

#include "fakedata.h"

int generateFakeData( int f, size_t n ) {
    file_resize( f, n );

    uint32_t i, j;
    int left, done, ret;
    char buf[4096];
    for( i = 0; i < n / 4; i += 1024 ) {
        if( !( i & 0x3FFFF ) )
            printf( "Status: %liM written\n", (long int)( i / ( 1 << 18 ) ) );
        for( j = 0; j < 1024 && j + i < n / 4; j++ )
            *(((uint32_t*) buf)+j) = htobe32( j+i );
        done = pwrite( f, buf, 4096, (i << 2) );
        left = 4096 - done;
        while( left > 0 ) {
            ret = pwrite( f, buf + done, left, (i << 2) + left );
            if( ret < 0 ) {
                perror( "more writing" );
                close( f );
                return -2;
            }
            done += ret;
            left -= ret;
        }
        if( left < 0 ) {
            perror( "writing" );
            close( f );
            return -2;
        }
        if( i == 0xFFFFFFFF - 1023 ) {
            printf( "Status: 16384M written\n" );
            break; // Prevent infinite loop on generating 16G
        }
    }
    if( !( i & 0x3FFFF ) )
        printf( "Status: %liM written\n", (long int)( i / ( 1 << 18 ) ) );

    struct stat st;
    fstat( f, &st );
    size_t size = st.st_size;
    if( size < 0 ) {
        perror( "reading size\n" );
        return -3;
    }
    if( size != n )
        printf( "Warning: size was supposed to be %lli, but turned out to be %lli.\n", (long long int)n, (long long int)size );

    close( f );

    return 0;
}
