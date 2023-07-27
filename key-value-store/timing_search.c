#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "api.h"


int main() {
    srand(time(NULL));

    Db *db = connect("timing.kv");
    use("trips", db);

    char *keys[3] = {
        "46093826 26:33:24",
        "45958860 9:15:00",
        "46017016 11:43:28"
    };

    for (int i = 0; i < 3; i++) {
        TreeNode *result = get(keys[i], db);
        if (result != NULL) {
            char *value = malloc(result->value_size + 1);
            memcpy(value, result->value, result->value_size);
            value[(int)result->value_size] = '\0';
            printf("value for key %s: '%s'\n", keys[i], value);
            free_safe(value);
        }
        else {
            printf("key %s not found\n", keys[i]);
        }
    }

    close(db);

    return 0;
}
