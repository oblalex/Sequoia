all: libmedia.so

libmedia.so: media.o
	gcc -shared media.o -o libmedia.so

media.o: media.c
	gcc -c -Wall -Werror -fpic media.c -o media.o

clean:
	rm -rf *.o
