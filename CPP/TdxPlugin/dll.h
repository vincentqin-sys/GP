#ifndef _DLL_H_
#define _DLL_H_

#define DLLIMPORT __declspec (dllexport)

#pragma pack(push,1) 
//����(���ݸ���,���,����a,����b,����c)
typedef void(*pPluginFUNC)(int,float*,float*,float*,float*);

typedef struct tagPluginTCalcFuncInfo {
	unsigned short		nFuncMark;//�������
	pPluginFUNC			pCallFunc;//������ַ在
} PluginTCalcFuncInfo;

typedef int(*pRegisterPluginFUNC)(PluginTCalcFuncInfo**);  
#pragma pack(pop)


extern "C" {
DLLIMPORT int RegisterTdxFunc(PluginTCalcFuncInfo** pFun);
}


#endif /* _DLL_H_ */
