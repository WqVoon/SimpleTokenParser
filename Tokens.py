import _io
from os import sys
from typing import List, Dict, Set, Any


class DebugOutput:
    """
    若 self.is_develop 为 True 则输出 Debug 信息，否则不输出
    文件提供 log 作为本类的全局实例，可在运行时动态修改
    """

    def __init__(self, output_msg):
        self.is_develop = output_msg

    def __call__(self, *msg):
        if self.is_develop:
            print("[DEBUG]", *msg, file=sys.stderr)


# 输出测试信息，改为 False 则不会输出
log = DebugOutput(False)


class ParseError(Exception):
    """
    Token 解析失败的异常
    """
    pass


class State:
    """
    自动机的一个状态，jmp_by 中保存着跳转规则
    """
    jmp_by: Dict[str, int]

    def __init__(self):
        self.jmp_by = {}


class AutoMachine:
    """
    识别模式用的自动机
    """
    end_states: Set[Any]
    states: Dict[int, State]

    def __init__(self):
        self.states = {}
        self.end_states = set()

    def make_pair(self, head_index: int, char: str, tail_index: int):
        """
        为某个状态增加一条跳转，若状态不存在则自动添加一个到状态集中

        :param head_index: 跳转弧的开始状态号
        :param char: 跳转弧的触发字符
        :param tail_index: 跳转弧的结束状态号
        :return: None
        """
        self.states.setdefault(head_index, State()).jmp_by[char] = tail_index
        self.states.setdefault(tail_index, State())

    def set_end(self, *index):
        """
        可变参数的函数，将参数中的状态号全部添加到结束状态集中

        :param index: 需要设置为结束状态的编号
        :return: None
        """
        for i in index:
            self.end_states.add(i)

    def validate(self, src: List[Any]):
        """
        根据自动机来识别序列中的字符

        :param src: 由待识别的字符序列组成的列表
        :return: tuple(src中不符合自动机模式的第一个字符下标, 是否识别成功, 是否识别到了src的末尾)
        """
        cur_state: int = 0
        index: int = 0
        is_end = False

        for index, char in enumerate(src, 0):
            try:
                assert isinstance(char, str)
                cur_state = self.states[cur_state].jmp_by[char]
            except KeyError:
                break
        else:
            is_end = True

        return (index if not is_end else index + 1,
                cur_state in self.end_states,
                is_end)


class TokenProcessor:
    buffer: List[str]
    file_handler: _io.TextIOWrapper

    double_size_char = (
        '->', '--', '-=', '++', '+=',
        '&=', '&&', '!=', '|=', '||',
        '<=', '<<', '>=', '>>', '*=',
        '/=', '%=', '^=', '##', '=='
    )

    triple_size_char = (
        '<<=', '>>=', '...'
    )

    KT = (
        'auto', 'char', 'const', 'double', 'enum', 'float',
        'inline', 'int', 'long', 'register', 'restrict',
        'short', 'signed', 'static', 'struct', 'typedef',
        'union', 'unsigned', 'void', 'volatile', 'include',
        'break', 'case', 'continue', 'default', 'do', 'else',
        'for', 'goto', 'if', 'return', 'sizeof', 'switch', 'while'
    )
    PT = (
        *triple_size_char, *double_size_char,
        '{', '}', '[', ']', '(', ')', '.', '&', '*',
        '+', '-', '~', '!', '/', '%', '<', '>', '^',
        '|', '?', ':', ';', '=', ',', '#'
    )

    def __init__(self, fh):
        self.file_handler = fh
        self.lineno = 1

        self.ch = ''
        self.tokens = []
        self.buffer = []

        self.iT = []
        self.cT = []
        self.ST = []
        self.CT = []
        self.ET = ()

        # TODO: 尝试把自动机设置为类公用的属性
        self.char_am = TokenProcessor.init_char_auto_machine()
        self.id_am = TokenProcessor.init_id_auto_machine()
        self.int_am = TokenProcessor.init_int_auto_machine()
        self.float_am = TokenProcessor.init_float_auto_machine()

        self.scan_file()

    def scan_file(self):
        """
        TODO: 尝试用 init_id_am 的字符串常量简化条件
        扫描 self.file_handler 指向的文件
        自动被 self.__init__ 调用

        :return: None
        """
        while True:
            self.buffer.clear()

            try:
                while self.ch.isalnum() or self.ch == '_' or self.ch == '.' \
                        or self.ch == '+' or self.ch == '-':
                    self.buffer.append(self.ch)
                    self.ch = self.getchar()

                if self.buffer:
                    self.match()
                    continue

                while not self.ch.isalnum() and self.ch != '_':
                    self.buffer.append(self.ch)
                    self.ch = self.getchar()

            except EOFError:
                break

            finally:
                self.match()

    def match(self):
        """
        分别调用各种匹配模式来匹配 self.buffer 中的字符流

        若其中一个模式匹配命中，则：
            生成 token 并将其加入到对应集合中
            从 self.buffer 裁剪掉命中的部分

        :return: None
        """
        while self.buffer:
            log("当前buffer:", self.buffer)
            if self.buffer[0].isspace() or not self.buffer[0]:
                log("判断为 [空字符]")
                if self.buffer.pop(0) == '\n':
                    self.lineno += 1
                continue

            if self.is_keywords():
                log("判断为 [关键字]")
                continue

            if self.is_id():
                log("判断为 [标识符]")
                continue

            if self.is_number():
                log("判断为 [数字]")
                continue

            if self.is_char():
                log("判断为 [字符]")
                continue

            if self.is_string():
                log("判断为 [字符串]")
                continue

            if self.is_partition():
                log("判断为 [界符]")
                continue

            log("判断为 [错误]")
            self.is_an_error(self.buffer.pop(0))

    def is_keywords(self):
        full_str = ''.join(self.buffer)

        try:
            token_id = self.KT.index(full_str)
            self.buffer.clear()
            self.tokens.append(('KT', token_id))
            target = True
        except ValueError:
            target = False

        return target

    def is_id(self):
        target: bool

        index, target, is_end = self.id_am.validate(self.buffer)

        if target:
            self.insert_token_into_symtable(index, 'iT')

        return target

    def is_number(self):
        index, target, is_end = self.float_am.validate(self.buffer)
        if not target:
            index, target, is_end = self.int_am.validate(self.buffer)

        if target:
            self.insert_token_into_symtable(index, 'CT')

        return target

    def is_char(self):
        if self.buffer[0] != '\'':
            return False

        quotation_index = self.read_char_until_quotation_mark('\'')
        if quotation_index == 2:
            self.is_an_error('', "单引号内不能为空")
            raise ParseError

        valid_index = 3
        if quotation_index > 3:
            valid_index, target, is_end = self.char_am.validate(self.buffer)

            if not target:
                valid_index = 2
            if self.buffer[valid_index] != '\'':
                self.is_an_error(''.join(self.buffer[:quotation_index]), "过长的字符:")

            self.buffer[valid_index] = '\''
            valid_index += 1

        self.insert_token_into_symtable(valid_index, 'cT')
        self.buffer[:quotation_index] = ''

        return True

    def is_string(self):
        if self.buffer[0] != '\"':
            return False

        # TODO: c 语言中可使用 \ 来分隔多行字符串
        index = self.read_char_until_quotation_mark('\"')

        self.insert_token_into_symtable(index, 'ST')

        return True

    def is_partition(self):
        buffer = self.buffer
        target = False
        tail_index = 1

        try:
            if len(buffer) >= 3 and \
                    self.is_triple_size_char(
                        buffer[0],
                        buffer[1],
                        buffer[2]):
                tail_index += 2

            elif len(buffer) >= 2 and \
                    self.is_double_size_char(
                        buffer[0],
                        buffer[1]):
                tail_index += 1

            char = ''.join(buffer[:tail_index])

            token_id = self.PT.index(char)
            self.tokens.append(('PT', token_id))
            buffer[:tail_index] = ''
            target = True

        except ValueError:
            pass

        return target

    def is_an_error(self, token: str, msg: str = "不合法的token:"):
        print("<'%s', line %d>" % (self.file_handler.name, self.lineno),
              msg, token, file=sys.stderr)

    def read_char_until_quotation_mark(self, mark: str):
        """
        读取字符到 self.buffer 中，直到遇到单引号或双引号

        :param mark: 单引号或双引号，其他符号暂时无意义
        :return: 后面的引号的下标 + 1
        """
        start_lineno: int = self.lineno
        pre = now = ''
        index = 1
        try:
            while pre == '\\' or now != mark:
                try:
                    pre = now
                    now = self.buffer[index]
                except IndexError:
                    log("尝试从文件中读取一个字符到buffer中")
                    now = self.ch
                    self.buffer.append(self.ch)
                    self.ch = self.getchar()
                    log("当前buffer:", self.buffer)
                finally:
                    if now == '\n':
                        raise ParseError
                    index += 1

        except (EOFError, ParseError) as err:
            log("字符或字符串不完整")
            self.lineno = start_lineno
            self.is_an_error(''.join(self.buffer[:index]), '引号不配对:')
            if isinstance(err, ParseError):
                raise err
            else:
                raise ParseError from err

        return index

    @staticmethod
    def is_double_size_char(char1, char2):
        """
        识别是否可以组成一个双字节字符

        :param char1: 第一个字符
        :param char2: 第二个字符
        :return: 是否匹配
        """
        for c1, c2 in TokenProcessor.double_size_char:
            if c1 == char1 and c2 == char2:
                return True
        else:
            return False

    @staticmethod
    def is_triple_size_char(char1, char2, char3):
        """
        识别是否可以组成一个三字节字符
        """
        for c1, c2, c3 in TokenProcessor.triple_size_char:
            if c1 == char1 and c2 == char2 and c3 == char3:
                return True
        else:
            return False

    def insert_token_into_symtable(self, tail, table_name):
        """
        将 self.buffer 中的一部分内容插入到 table_name 指定的符号表中
        同时将这部分内容从 self.buffer 中清空

        :param tail: self.buffer 中有效部分的长度加一
        :param table_name: 试图插入的符号表名
        :return:
        """
        token_id = 0
        full_str = ''.join(self.buffer[:tail])
        try:
            token_id = self[table_name].index(full_str)
        except ValueError:
            self[table_name].append(full_str)
            token_id = len(self[table_name]) - 1
        finally:
            self.tokens.append((table_name, token_id))
            self.buffer = self.buffer[tail:]

    def getchar(self):
        """
        从 self.file_handler 中读取一个字符
        如果读取到空字符则抛出 EOFError

        :return: 读取到的字符
        """
        tmp = self.file_handler.read(1)
        if not tmp:
            raise EOFError
        return tmp

    def __getitem__(self, item: str):
        if 'iT' == item:
            return self.iT
        elif 'cT' == item:
            return self.cT
        elif 'ST' == item:
            return self.ST
        elif 'CT' == item:
            return self.CT
        elif 'KT' == item:
            return self.KT
        elif 'PT' == item:
            return self.PT
        elif 'ET' == item:
            return self.ET
        else:
            raise ValueError

    def __iter__(self):
        return self.tokens.__iter__()

    @classmethod
    def init_int_auto_machine(cls):
        valid_char = "abcdefABCDEF"
        am = AutoMachine()

        am.make_pair(0, '0', 2)

        for i in range(1, 10):
            am.make_pair(0, str(i), 1)

        for i in range(10):
            am.make_pair(1, str(i), 1)
            am.make_pair(4, str(i), 5)

        for i in range(8):
            am.make_pair(2, str(i), 3)
            am.make_pair(3, str(i), 3)

        am.make_pair(2, 'x', 4)
        am.make_pair(2, 'X', 4)

        for i in valid_char:
            am.make_pair(4, i, 5)
            am.make_pair(5, i, 5)

        am.set_end(1, 2, 3, 5)

        return am

    @classmethod
    def init_float_auto_machine(cls):
        am = AutoMachine()

        am.make_pair(0, '.', 1)
        am.make_pair(3, '.', 2)

        for i in range(10):
            tmp: str = str(i)
            am.make_pair(1, tmp, 2)
            am.make_pair(0, tmp, 3)
            am.make_pair(2, tmp, 2)
            am.make_pair(3, tmp, 3)
            am.make_pair(4, tmp, 6)
            am.make_pair(5, tmp, 6)
            am.make_pair(6, tmp, 6)

        am.make_pair(2, 'E', 4)
        am.make_pair(2, 'e', 4)

        am.make_pair(4, '+', 5)
        am.make_pair(4, '-', 5)

        am.set_end(2, 6)

        return am

    @classmethod
    def init_id_auto_machine(cls):
        valid_char = \
            "_abcdefghijklmnopqrstuvwxyz" \
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
            "0123456789"

        am = AutoMachine()

        for ch in valid_char[:53]:
            am.make_pair(0, ch, 1)

        for ch in valid_char:
            am.make_pair(1, ch, 1)

        am.set_end(1)

        return am

    @classmethod
    def init_char_auto_machine(cls):
        valid_char = '\\abfnrtv0123456789abcdefABCDEF'

        am = AutoMachine()

        am.make_pair(0, '\'', 0)
        am.make_pair(0, '\\', 1)

        for i in valid_char[:8]:
            am.make_pair(1, i, 7)

        for i in range(8):
            tmp = str(i)
            am.make_pair(1, tmp, 2)
            am.make_pair(2, tmp, 3)
            am.make_pair(3, tmp, 4)

        am.make_pair(1, 'x', 5)
        am.make_pair(1, 'X', 5)

        for i in valid_char[8:]:
            am.make_pair(5, i, 6)
            am.make_pair(6, i, 6)

        am.set_end(2, 3, 4, 6, 7)

        return am
