import _io
from typing import List, Dict, Set, Any


def debug_output(is_debug):
    def output(msg):
        if is_debug:
            print(msg)

    return output


# 输出测试信息，改为 False 则不会输出
log = debug_output(True)


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
    file_handler: _io.TextIOWrapper

    def __init__(self, fh):
        self.file_handler = fh
        self.get_eof = False

        self.ch = ''
        self.tokens = []
        self.buffer = []

        self.iT = []
        self.cT = []
        self.ST = []
        self.CT = []
        self.KT = []
        self.PT = []
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
        while not self.get_eof:
            self.buffer.clear()

            while self.ch.isalnum() or self.ch == '_' or self.ch == '.':
                self.buffer.append(self.ch)
                self.ch = self.getchar()

            if self.buffer:
                self.match()
                continue

            while not self.ch.isalnum() and self.ch != '_':
                self.buffer.append(self.ch)
                self.ch = self.getchar()

            self.match()

    def match(self):
        """
        TODO: 解决匹配时一直循环的问题
        分别调用各种匹配模式来匹配 self.buffer 中的字符流

        若其中一个模式匹配命中，则：
            生成 token 并将其加入到对应集合中
            从 self.buffer 裁剪掉命中的部分

        :return: None
        """
        while self.buffer:
            if self.is_keywords():
                continue
            log("test keywords")
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
            self.is_an_error()

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

        index, target, is_end = self.int_am.validate(self.buffer)
        if not target:
            index, target, is_end = self.float_am.validate(self.buffer)
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
        target = False

        for index, char in enumerate(self.buffer, 0):
            try:
                token_id = self.PT.index(char)
                self.tokens.append(('PT', token_id))
                self.buffer.pop(0)
                target = True
            except ValueError:
                break

        return target

    def is_an_error(self):
        pass

    def getchar(self):
        """
        从 self.file_handler 中读取一个字符
        如果读取到空字符则设置 self.get_eof 为 True

        :return: 读取到的字符
        """
        tmp = self.file_handler.read(1)
        if not tmp:
            self.get_eof = True
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
