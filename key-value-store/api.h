#ifndef __api__
#define __api__


#include <stdio.h>

#include "io.h"
#include "table.h"


typedef struct db {
    char *path;
    FILE *fp;
    Table *user_tb;
    Table *master_tb;
} Db;


void use(char *, Db *);

void close(Db *);

void db_delete(char *, Db *);

Record *get(char *, Db *);

void put(char *, void *, long, Db *);

Db *connect(char *);


#endif
