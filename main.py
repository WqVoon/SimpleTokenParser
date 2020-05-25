import _io
from typing import List, Dict, Set, Any


def debug_output(is_debug):
    def output(*msg):
        if is_debug:
            print("[DEBUG]", *msg)

    return output


# 输出测试信息，改为 False 则不会输出
log = debug_output(False)


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

        return index, cur_state in self.end_states, is_end


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
        'union', 'unsigned', 'void', 'volatile',
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

        self.ch = ''
        self.tokens = []
        self.buffer = []

        self.iT = []
        self.cT = []
        self.ST = []
        self.CT = []
        self.ET = ()

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
                self.buffer.pop(0)
                continue

            log("test keywords")
            if self.is_keywords():
                continue

            log("test identifier")
            if self.is_id():
                continue

            log("test number")
            if self.is_number():
                continue

            log("test char")
            if self.is_char():
                continue

            log("test string")
            if self.is_string():
                continue

            log("test partition")
            if self.is_partition():
                continue

            log("error")
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
        token_id = 0

        index, target, is_end = self.id_am.validate(self.buffer)
        index = index + 1 if is_end else index

        if target:
            full_str = ''.join(self.buffer[:index])
            try:
                token_id = self.iT.index(full_str)
            except ValueError:
                self.iT.append(full_str)
                token_id = len(self.iT) - 1
            finally:
                self.tokens.append(('iT', token_id))
                self.buffer = self.buffer[index:]

        return target

    def is_number(self):
        token_id = 0

        index, target, is_end = self.float_am.validate(self.buffer)
        if not target:
            index, target, is_end = self.int_am.validate(self.buffer)
        index = index + 1 if is_end else index

        if target:
            full_str = ''.join(self.buffer[:index])
            try:
                token_id = self.CT.index(full_str)
            except ValueError:
                self.CT.append(full_str)
                token_id = len(self.CT) - 1
            finally:
                self.tokens.append(('CT', token_id))
                self.buffer = self.buffer[index:]

        return target

    def is_char(self):
        pass

    def is_string(self):
        pass

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

    @staticmethod
    def is_an_error(token):
        log("不合法的token：", token)

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
        am = AutoMachine()

        am.make_pair(0, '', 0)
        am.make_pair(1, '', 1)

        # TODO: 这里的 1 使得自动机无法识别数字0，但为了其他进制数所以先不改
        for i in range(1, 9):
            am.make_pair(0, str(i), 1)

        for i in range(9):
            am.make_pair(1, str(i), 1)

        am.set_end(1)

        return am

    @classmethod
    def init_float_auto_machine(cls):
        am = AutoMachine()

        for i in range(6):
            am.make_pair(i, '', i)

        am.make_pair(0, '.', 1)
        am.make_pair(3, '.', 2)

        for i in range(9):
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

        am.make_pair(0, '', 0)
        am.make_pair(1, '', 1)

        for ch in valid_char[:53]:
            am.make_pair(0, ch, 1)

        for ch in valid_char:
            am.make_pair(1, ch, 1)

        am.set_end(1)

        return am
