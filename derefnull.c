/**
* @file derefnull.c
* @author Jas Eckard <jas@eckard.com>
*
* @section LICENSE
*
* (GPL license?)
*
* @section DESCRIPTION
*
* This file tests null pointer dereferencing

* Output in Linux:

tiger[00:21:20](139)(master)~/src/cpsc8240$ ./derefnull
NULL is '(null)', but something is 'something'.
Segmentation fault

* Output in xv6:


*/

//#include <stddef.h>
#include <stdio.h>

int main(int argc, char **argv)
{
        int *nil = NULL;
        char *null = NULL;
        char *something = "something";

        printf("NULL is '%s', but something is '%s'.\n", null, something);
        printf("NULL is '%d'.", *nil);

        return 0;
}
