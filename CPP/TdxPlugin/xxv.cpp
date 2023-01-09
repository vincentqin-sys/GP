#include "mysql.h"
#include <stdio.h>
#include "hgt.h"

int main(int argc, char **argv) {
	float out[100];
	float code = 600233;
	GetJGD(100, out, &code, NULL, NULL);
	printf("%d %d %f \n", (int)out[99], (int)out[98], out[97]);
	return 0;
}