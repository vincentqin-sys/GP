
#include <windows.h>
#include "mysql.h"
#include <stdio.h>
#include <stdlib.h>
#include "hgt.h"

char *gbk2utf8(char *gbk) {
	wchar_t wname[50] = {0};
	char *name = (char *)malloc(120);
	memset(name, 0, 120);
	MultiByteToWideChar(CP_ACP, 0, gbk, -1, wname, 50);
	WideCharToMultiByte(CP_UTF8, 0, wname, -1, name, 120, NULL, NULL);
	return name;
}

int main(int argc, char **argv) {
	/*
	Mysql db;
	ResultSet *rs;
	db.connect("tdx_f10");
	rs = db.query("select _code, _name, _hy from _base");

	FILE *file = fopen("base.txt", "w");
	char tmp[200];

	for (int i = 0; rs->next(); ++i)
	{
		char *code = rs->getString(0);
		char *name = (rs->getString(1));
		char *hy = (rs->getString(2));
		printf("[%d] %s %s %s \n", i, code, name, hy);

		name = gbk2utf8(name);
		hy = gbk2utf8(hy);
		sprintf(tmp, "%s\t%s\t%s\n", code, name, hy);
		fwrite(tmp, strlen(tmp), 1, file);
	}
	fclose(file);
	db.close();
	*/
	return 0;
}