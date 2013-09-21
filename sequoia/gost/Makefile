all: libgost.so

libgost.so: gost.o
	gcc -shared gost.o -o libgost.so

gost.o: gost.c
	gcc -c -Wall -Werror -fpic gost.c -o gost.o

clean:
	rm -rf *.o
