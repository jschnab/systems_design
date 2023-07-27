#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "api.h"

#define BUFSZ 256

int main() {
    srand(time(NULL));

    char sInputBuf[BUFSZ];
    char *tok;
    int trip_id;
    char *arrival_time;
    char *departure_time;
    int stop_id;
    int stop_sequence;
    char *stop_headsign;
    int pickup_type;
    int drop_off_type;
    float shape_dist_traveled;
   
    Db *db = connect("timing.kv");
    use("trips", db);

    FILE *pFile = fopen("data.csv", "r");
    int n = 0;

    char key[30];
    char value[100];
    int value_size = 0;

    while (!feof(pFile)) {
        fgets(sInputBuf, BUFSZ, pFile);

        tok = strtok(sInputBuf, ",");
        trip_id = tok ? atoi(tok) : 0;
        tok = strtok(NULL, ",");
        arrival_time = tok ? tok : "";
        tok = strtok(NULL, ",");
        departure_time = tok ? tok : "";
        tok = strtok(NULL, ",");
        stop_id = tok ? atoi(tok) : 0;
        tok = strtok(NULL, ",");
        stop_sequence = tok ? atoi(tok) : 0;
        tok = strtok(NULL, ",");
        stop_headsign = tok ? tok : "";
        tok = strtok(NULL, ",");
        pickup_type = tok ? atoi(tok) : 0;
        tok = strtok(NULL, ",");
        drop_off_type = tok ? atoi(tok) : 0;
        tok = strtok(NULL, ",");
        shape_dist_traveled = tok ? atof(tok) : 0;

        sprintf(key, "%d %s", trip_id, arrival_time);
        sprintf(value, "%s,%d,%d,%s,%d,%d,%f", departure_time, stop_id, stop_sequence, stop_headsign, pickup_type, drop_off_type, shape_dist_traveled);
        value_size = strlen(value);

        put(key, value, value_size, db);
        n++;

        if (n % 500000 == 0) {
            printf("loaded %d records\n", n);
        }
    }

    printf("loaded all %d records\n", n);

    close(db);

    return 0;
}
