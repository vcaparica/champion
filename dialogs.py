import ctypes
from ctypes import wintypes


if not hasattr(wintypes, "LRESULT"):
    wintypes.LRESULT = ctypes.c_ssize_t
if not hasattr(wintypes, "INT_PTR"):
    wintypes.INT_PTR = ctypes.c_ssize_t
if not hasattr(wintypes, "UINT_PTR"):
    wintypes.UINT_PTR = ctypes.c_size_t
if not hasattr(wintypes, "LONG_PTR"):
    wintypes.LONG_PTR = ctypes.c_ssize_t
if not hasattr(wintypes, "ULONG_PTR"):
    wintypes.ULONG_PTR = ctypes.c_size_t
if not hasattr(wintypes, "HCURSOR"):
    wintypes.HCURSOR = wintypes.HANDLE
if not hasattr(wintypes, "HICON"):
    wintypes.HICON = wintypes.HANDLE
if not hasattr(wintypes, "HBRUSH"):
    wintypes.HBRUSH = wintypes.HANDLE

def alert_box(title, message):
    MB_OK = 0x00000000
    result = ctypes.windll.user32.MessageBoxW(0, message, title, MB_OK)
    return result

def dialog_box(title, message):
    MB_OKCANCEL = 0x00000001
    result = ctypes.windll.user32.MessageBoxW(0, message, title, MB_OKCANCEL)
    return result

def question_box(title, message):
    MB_YESNO = 0x00000004
    result = ctypes.windll.user32.MessageBoxW(0, message, title, MB_YESNO)
    return result

def input_box(title, message, prefill_text=""):
    import struct

    user32 = ctypes.windll.user32

    # --- Win32 constants ---
    WS_POPUP = 0x80000000
    WS_CAPTION = 0x00C00000
    WS_SYSMENU = 0x00080000
    DS_MODALFRAME = 0x00000080
    DS_SETFONT = 0x00000040
    DS_CENTER = 0x00000800

    WS_VISIBLE = 0x10000000
    WS_CHILD = 0x40000000
    WS_TABSTOP = 0x00010000
    WS_GROUP = 0x00020000
    WS_BORDER = 0x00800000

    ES_LEFT = 0x0000
    ES_AUTOHSCROLL = 0x0080

    BS_DEFPUSHBUTTON = 0x00000001
    BS_PUSHBUTTON = 0x00000000

    WM_INITDIALOG = 0x0110
    WM_COMMAND = 0x0111

    EM_SETSEL = 0x00B1

    IDOK = 1
    IDCANCEL = 2
    IDC_EDIT = 1001
    IDC_PROMPT = 1002

    # Predefined class atoms
    ATOM_BUTTON = 0x0080
    ATOM_EDIT = 0x0081
    ATOM_STATIC = 0x0082

    def _align_dword(b: bytearray) -> None:
        while (len(b) % 4) != 0:
            b.append(0)

    def _word(b: bytearray, v: int) -> None:
        b.extend(struct.pack('<H', v & 0xFFFF))

    def _dword(b: bytearray, v: int) -> None:
        b.extend(struct.pack('<I', v & 0xFFFFFFFF))

    def _short(b: bytearray, v: int) -> None:
        b.extend(struct.pack('<h', int(v)))

    def _wstr(b: bytearray, s: str) -> None:
        if s is None:
            s = ''
        b.extend((s + '\0').encode('utf-16le'))

    def _class_atom(b: bytearray, atom: int) -> None:
        # 0xFFFF followed by atom (WORD)
        _word(b, 0xFFFF)
        _word(b, atom)

    # --- Dialog template header ---
    dlg_style = WS_POPUP | WS_CAPTION | WS_SYSMENU | DS_MODALFRAME | DS_SETFONT | DS_CENTER
    dlg_ex_style = 0

    # Dialog units (fine for typical font). You can tweak if desired.
    dlg_x, dlg_y, dlg_cx, dlg_cy = 10, 10, 230, 86

    cdit = 4  # prompt, edit, ok, cancel

    buf = bytearray()
    _dword(buf, dlg_style)
    _dword(buf, dlg_ex_style)
    _word(buf, cdit)
    _short(buf, dlg_x)
    _short(buf, dlg_y)
    _short(buf, dlg_cx)
    _short(buf, dlg_cy)

    # menu = none, class = default, title
    _word(buf, 0)
    _word(buf, 0)
    _wstr(buf, title)

    # DS_SETFONT: font size + face name
    _word(buf, 9)  # point size
    _wstr(buf, 'MS Shell Dlg')

    # --- Control 1: STATIC prompt ---
    _align_dword(buf)
    _dword(buf, WS_CHILD | WS_VISIBLE)  # style
    _dword(buf, 0)                      # exstyle
    _short(buf, 7); _short(buf, 7); _short(buf, 216); _short(buf, 18)  # x,y,cx,cy
    _word(buf, IDC_PROMPT)
    _class_atom(buf, ATOM_STATIC)
    _wstr(buf, '')
    _word(buf, 0)  # no creation data

    # --- Control 2: EDIT (single line) ---
    _align_dword(buf)
    _dword(buf, WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_LEFT | ES_AUTOHSCROLL)
    _dword(buf, 0)
    _short(buf, 7); _short(buf, 28); _short(buf, 216); _short(buf, 12)
    _word(buf, IDC_EDIT)
    _class_atom(buf, ATOM_EDIT)
    _wstr(buf, '')
    _word(buf, 0)

    # --- Control 3: OK (default) ---
    _align_dword(buf)
    _dword(buf, WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_GROUP | BS_DEFPUSHBUTTON)
    _dword(buf, 0)
    _short(buf, 92); _short(buf, 52); _short(buf, 55); _short(buf, 14)
    _word(buf, IDOK)
    _class_atom(buf, ATOM_BUTTON)
    _wstr(buf, 'OK')
    _word(buf, 0)

    # --- Control 4: Cancel ---
    _align_dword(buf)
    _dword(buf, WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON)
    _dword(buf, 0)
    _short(buf, 150); _short(buf, 52); _short(buf, 65); _short(buf, 14)
    _word(buf, IDCANCEL)
    _class_atom(buf, ATOM_BUTTON)
    _wstr(buf, 'Cancel')
    _word(buf, 0)

    template = (ctypes.c_ubyte * len(buf)).from_buffer_copy(bytes(buf))

    # --- Dialog procedure ---
    result_text = {'cancelled': True, 'text': ''}

    DLGPROC = ctypes.WINFUNCTYPE(wintypes.INT_PTR, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    @DLGPROC
    def dlgproc(hDlg, uMsg, wParam, lParam):
        if uMsg == WM_INITDIALOG:
            user32.SetDlgItemTextW(hDlg, IDC_PROMPT, message)
            user32.SetDlgItemTextW(hDlg, IDC_EDIT, prefill_text)

            hEdit = user32.GetDlgItem(hDlg, IDC_EDIT)
            if hEdit:
                user32.SetFocus(hEdit)
                user32.SendMessageW(hEdit, EM_SETSEL, 0, -1)
            # returning 0 because we manually set focus
            return 0

        if uMsg == WM_COMMAND:
            cmd = int(wParam) & 0xFFFF
            if cmd == IDOK:
                hEdit = user32.GetDlgItem(hDlg, IDC_EDIT)
                if hEdit:
                    length = user32.GetWindowTextLengthW(hEdit)
                    buf2 = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hEdit, buf2, length + 1)
                    result_text['text'] = buf2.value
                result_text['cancelled'] = False
                user32.EndDialog(hDlg, IDOK)
                return 1

            if cmd == IDCANCEL:
                result_text['cancelled'] = True
                user32.EndDialog(hDlg, IDCANCEL)
                return 1

        return 0

    # 0 = HWND_DESKTOP (owner). If you have a pygame window handle, you can pass it here.
    user32.DialogBoxIndirectParamW(0, ctypes.cast(template, wintypes.LPCVOID), 0, dlgproc, 0)

    if result_text['cancelled']:
        return -1
    return result_text['text']
