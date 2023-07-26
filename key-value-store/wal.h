#ifndef __wal__
#define __wal__

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "alloc.h"
#include "tree.h"


/*
   WAL item structure:

   Element        | Size (bytes)   |         Offset (bytes)
   --------------------------------------------------------
   record length  |       4        |               0
   WAL command    |       1        |               4
   key length     |       1        |               5
   key            |   key length   |               6
   value          |    variable    |         6 + key length


   Index item length: 1 + start key size + end key size + 8

*/


/* Interface command codes for WAL. */
#define INSERT 1
#define DELETE 2
/* Interface command codes specific to master table WAL. */ 
#define CREATE_NS 3

/* Write-Ahead Log offsets and sizes. */
#define WAL_CMD_SZ 1


RBTree *restore_wal(FILE *, unsigned long);

FILE *truncate_wal(char *, FILE *);

void write_wal_command(char, char *, void *, long, FILE *);

void write_wal_header(FILE *);


#endif
