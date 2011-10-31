#include <stdio.h>
#include <string.h>
#include "sha1.h"

/*
 * The calculation of a root hash consists of building the complete hash tree (64 levels deep) and finding the top hash.
 * The bottom leafs are filled, from left to right (i.e. leafs (0,0), (0,1), (0,2), ...), with the SHA1 hashes of the data chopped into 1kB chunks.
 * Each parent node is then the SHA1 hash of the concatenation of the hashes in its children.
 * All leafs that do not get filled are set to hash ZERO (that is: 20 null-bytes), the same goes for all nodes with two ZERO children.
 * The hash tree is emulated using a simple array that stores only one hash per level.
 * Since the file is read sequentially all the hashes can be calculated sequentially and no more than one hash per level needs to be remembered at any time.
 * The procedure is simple: if a level has no hash remembered, the hash currently being inserted is the left sibling on that level and needs to be remembered.
 * If a level has a hash remembered, that hash currently being inserted is the right sibling on that level and hence the parent of the two can be calculated.
 * Note that, once the parent of two hashes is calculated, the hashes themselves will never be used again, and can hence be forgotten.
 */

int main( int argc, char** argv ) {
    /* A buffer for reading a kilobyte of data */
    char buffer[1024];
    /* An array to keep track of which areas of hashes are in use */
    unsigned char hashSet[64];
    /* The array of hashes, that will be used to emulate the hash tree. Contains up to 64 hashes at positions hashes, hashes+20, hashes+40, etc */
    unsigned char hashes[20*64];
    /* A single hash, the one we're currently working with */
    unsigned char hash[20];
    /* The datastructure for SHA1 routines */
    blk_SHA_CTX h;
    /* The number of bytes read */
    int sizeRead;
    int i;
    FILE* f;
    
    if( argc < 2 ) {
        printf( "Usage: %s file\nCalculates the SHA1 root hash of the file.\n", argv[0] );
        return 1;
    }

    /* Open the file for reading */
    f = fopen( argv[1], "r" );
    if( !f ) {
        printf( "Error: Could not open file %s for reading", argv[1] );
        return 2;
    }
    if( ferror( f ) ) {
        printf( "Error before reading %s: %d\n", argv[1], ferror( f ) );
        return 3;
    }

    /* Initialize the buffer and hash arrays */
    bzero( hashes, 20*64 );
    for( i = 0; i < 64; i++ )
        hashSet[i] = 0;

    /* Read the file, kilobyte by kilobyte, and build the hash tree */
    /*
     * If needed for debug, one can enable these statements.
    int count[64];
    int j;
    for( j = 0; j < 64; j++ )
        count[j] = 0;
    */
    while( !feof( f ) ) {
        sizeRead = fread( buffer, 1, 1024, f );
        if( ferror( f ) ) {
            printf( "Error while reading %s: %d\n", argv[1], ferror( f ) );
            fclose( f );
            return 3;
        }

        if( !sizeRead ) {
            /* Catch the corner case where we read 0 bytes. This is also EOF. */
            break;
        }

        /* Create the SHA1 hash of the kilobyte that has just been read */
        blk_SHA1_Init( &h );
        blk_SHA1_Update( &h, buffer, sizeRead );
        blk_SHA1_Final( hash, &h );

        /*
        fprintf( stderr, "(0,%d) : ", count[0]++ );
        for( j = 0; j < 20; j++ )
            fprintf( stderr, "%02x", (unsigned int)hash[j] );
        fprintf( stderr, "\n" );
        */

        /* Add the hash to the hash tree: going from bottom to top, find the first empty spot to insert the hash into, merging all the hashes found before that into this one. */
        for( i = 0; i < 64; i++ ) {
            if( !hashSet[i] ) {
                /* Emtpy spot: we are the left sibling of the split on level i, copy the hash into the tree */
                memcpy( hashes+(i*20), hash, 20 );
                hashSet[i] = 1;
                break;
            }
            else {
                /* Occupied spot: we are the right sibling of the split on level i, so merge the hashes (Sha1Hash( left-hash || right-hash )) and propagate that to the parent of the split. */
                blk_SHA1_Init( &h );
                blk_SHA1_Update( &h, hashes+(i*20), 20 );
                blk_SHA1_Update( &h, hash, 20 );
                blk_SHA1_Final( hash, &h );
                hashSet[i] = 0;
                /*
                fprintf( stderr, "(%d,%d) : ", i+1, count[i+1]++ );
                for( j = 0; j < 20; j++ )
                    fprintf( stderr, "%02x", (unsigned int)hash[j] );
                fprintf( stderr, "\n" );
                */
            }
        }
    }
    fclose( f );

    /* Now that all data has been read, all that is needed is to find hash (63,0) and we're done. First find the lowest level with a remembered hash and set the current hash to ZERO. */
    bzero( hash, 20 );
    i = 0;
    while( !hashSet[i] && i < 64 )
        i++;

    if( i == 63 ) {
        /* Special case: tree was filled with a maximum sized file, so root has already been calculated */
        memcpy( hash, hashes+63*20, 20 );
    }

    /* Now combine the remembered hashes and newly calculated hashes with ZERO where needed and propagate all results up to find the root hash. */
    while( i < 63 ) {
        blk_SHA1_Init( &h );
        if( !hashSet[i] ) {
            /* Empty spot: we are the left sibling of the split on level i, so the right sibling is ZERO. Merge the hashes and propagate that to the parent of the split. */
            blk_SHA1_Update( &h, hash, 20 );
            blk_SHA1_Update( &h, hashes+63*20, 20 );  /* Note that hashSet[63] will always remain 0. As such, we can use hashes+(63*20) to read 20 zero bytes, since they will remain zero as well. */
        }
        else {
            /* Occupied spot: we are the right sibling of the split on level i, so merge the hashes and propagate that to the parent of the split. */
            blk_SHA1_Update( &h, hashes+(i*20), 20 );
            blk_SHA1_Update( &h, hash, 20 );
        }
        blk_SHA1_Final( hash, &h );
        i++;
    }

    /* After all these calculations, we'll have the hash for bin (63,0) in hash. */
    for( i = 0; i < 20; i++ )
        printf( "%02x", (unsigned int)hash[i] );

    return 0;
}
