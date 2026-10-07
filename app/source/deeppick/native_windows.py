"""Windows security and Shell links without launching command-line helpers."""
from __future__ import annotations

import ctypes
import uuid
from ctypes import wintypes
from functools import lru_cache


@lru_cache(maxsize=1)
def current_sid():
    advapi = ctypes.WinDLL('advapi32',use_last_error=True)
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p,ctypes.POINTER(wintypes.LPWSTR)]
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        needed = wintypes.DWORD()
        advapi.GetTokenInformation(token,1,None,0,ctypes.byref(needed))
        buffer = ctypes.create_string_buffer(needed.value)
        if not advapi.GetTokenInformation(token,1,buffer,needed,ctypes.byref(needed)):
            raise ctypes.WinError(ctypes.get_last_error())
        pointer = ctypes.cast(buffer,ctypes.POINTER(ctypes.c_void_p))[0]
        text = wintypes.LPWSTR()
        if not advapi.ConvertSidToStringSidW(pointer,ctypes.byref(text)):
            raise ctypes.WinError(ctypes.get_last_error())
        try: return text.value
        finally: kernel.LocalFree(text)
    finally: kernel.CloseHandle(token)


def secure_acl(path):
    advapi = ctypes.WinDLL('advapi32',use_last_error=True)
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,ctypes.POINTER(ctypes.c_void_p),ctypes.c_void_p]
    advapi.GetSecurityDescriptorDacl.argtypes = [ctypes.c_void_p,ctypes.POINTER(wintypes.BOOL),ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(wintypes.BOOL)]
    advapi.SetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR,ctypes.c_int,wintypes.DWORD,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]
    advapi.SetNamedSecurityInfoW.restype = wintypes.DWORD
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    inheritance = 'OICI' if path.is_dir() else ''
    sddl = f'D:P(A;{inheritance};FA;;;{current_sid()})(A;{inheritance};FA;;;SY)'
    descriptor = ctypes.c_void_p()
    if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,ctypes.byref(descriptor),None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        present,defaulted = wintypes.BOOL(),wintypes.BOOL()
        dacl = ctypes.c_void_p()
        if not advapi.GetSecurityDescriptorDacl(descriptor,ctypes.byref(present),ctypes.byref(dacl),ctypes.byref(defaulted)) or not present.value:
            raise ctypes.WinError(ctypes.get_last_error())
        result = advapi.SetNamedSecurityInfoW(str(path),1,0x80000004,None,None,dacl,None)
        if result: raise ctypes.WinError(result)
    finally: kernel.LocalFree(descriptor)


class Guid(ctypes.Structure):
    _fields_ = [('data1',wintypes.DWORD),('data2',wintypes.WORD),('data3',wintypes.WORD),('data4',ctypes.c_ubyte*8)]

    @classmethod
    def parse(cls,text): return cls.from_buffer_copy(uuid.UUID(text).bytes_le)


def _check_hresult(value):
    if value < 0: raise OSError(f'Windows Shell 错误：0x{value & 0xffffffff:08X}')


def _method(pointer,index,*types):
    table = ctypes.cast(pointer,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return ctypes.WINFUNCTYPE(wintypes.LONG,ctypes.c_void_p,*types)(table[index])


def write_shortcut(target,path,arguments=''):
    ole = ctypes.WinDLL('ole32',use_last_error=True)
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p,wintypes.DWORD]
    ole.CoInitializeEx.restype = wintypes.LONG
    ole.CoCreateInstance.argtypes = [ctypes.POINTER(Guid),ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Guid),ctypes.POINTER(ctypes.c_void_p)]
    ole.CoCreateInstance.restype = wintypes.LONG
    initialized = ole.CoInitializeEx(None,2)
    if initialized != -2147417850: _check_hresult(initialized)
    link,persist = ctypes.c_void_p(),ctypes.c_void_p()
    try:
        clsid = Guid.parse('00021401-0000-0000-C000-000000000046')
        iid = Guid.parse('000214F9-0000-0000-C000-000000000046')
        _check_hresult(ole.CoCreateInstance(ctypes.byref(clsid),None,1,ctypes.byref(iid),ctypes.byref(link)))
        for index,text in ((20,str(target)),(9,str(target.parent)),(11,arguments),(7,'DeepPick AI - Developer:Chunze Liu')):
            _check_hresult(_method(link,index,wintypes.LPCWSTR)(link,text))
        icon = target.parent / 'app/source/assets/DeepPickAI.ico'
        _check_hresult(_method(link,17,wintypes.LPCWSTR,ctypes.c_int)(link,str(icon if icon.is_file() else target),0))
        _check_hresult(_method(link,15,ctypes.c_int)(link,1))
        iid_file = Guid.parse('0000010B-0000-0000-C000-000000000046')
        _check_hresult(_method(link,0,ctypes.POINTER(Guid),ctypes.POINTER(ctypes.c_void_p))(link,ctypes.byref(iid_file),ctypes.byref(persist)))
        _check_hresult(_method(persist,6,wintypes.LPCWSTR,wintypes.BOOL)(persist,str(path),True))
    finally:
        if persist: _method(persist,2)(persist)
        if link: _method(link,2)(link)
        if initialized >= 0: ole.CoUninitialize()
