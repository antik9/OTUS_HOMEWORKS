## Some patches for python v2.7

**opcode.patch** creates new operator in python binaries in case whether LOAD_FAST and LOAD_CONST with value 0 are concatenated
int the call stack

**until.patch** creates new statement in python. Until is common programming language statement, it starts loop until bool
value of until statement becomes true
```
>>> num = 3
>>> until num == 0:
...   print(num)
...   num -= 1
...
3
2
1
>>>
```

**incr.patch** create increment and decrement operators.
```
>>> test = 1
>>> test++
>>> test
2
>>>
```
