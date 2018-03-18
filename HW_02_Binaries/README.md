## Some patches for python v2.7

**opcode.patch** creates new operator in python binaries in case whether **LOAD_FAST** and **LOAD_CONST** with zero value are concatenated in the call stack

**until.patch** creates new statement in python. Until is common programming language statement, it starts infinite loop which breaks when bool value of until statement set to true
```
>>> num = 3
>>> until num == 0:
...   print(num)
...   num -= 1
...
3
2
1
```

**incr.patch** creates postfix increment and decrement operators, which are common in most programming languages. For example in C-family languages like C, C++, Java...
```
>>> test = 1
>>> test++
>>> test
2
>>> test--
>>> test
1
```
