''' 为同一字符串序列的不同大小写形式生成不碰撞的字符串。以便在大小写不敏感的系统中存储同一字符串的不同形式。 '''

from io import StringIO

def human_readable_upper_part_map(string: str, backward: bool):
    ''' 找到字符串中所有的 ASCII 大写字母，并返回一个能表示他们绝对位置的字符串。
        其中每个非相邻的大写字母之间用数字表示相隔的字符数。

        params: backward: 可以表示是正着看还是倒着看。
        
        NOTE: 在我们的用例中，我们 backward = True ，这样产生的 upper_part 就不太像 BV 号或者类似的编号，以免 upper_part 污染全文搜索。

        例如：
        backward = False
            BV1HP411D7Rj -> BV1HP3D1R （长得像 bvid ）
        backward = True
            BV1HP411D7Rj -> 1R1D3PH1VB
    '''

    assert backward

    if backward:
        string = string[::-1]

    result = StringIO()
    steps = 0
    for char in string:
        if char.isascii() and char.isupper():
            if steps == 0:
                result.write(char)
            else:
                result.write(f'{steps}{char}')
            steps = 0
        else:
            steps += 1

    return result.getvalue()