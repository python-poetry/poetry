# Python code to illustrate append() mode 
file = open('geek.txt','a') 
file.write("This will add this line") 
file.close() 

# Python code to illustrate with() 
with open("file.txt") as file:   
    data = file.read()  
# do something with data  


# Python code to illustrate with() alongwith write() 
with open("file.txt", "w") as f:  
    f.write("Hello World!!!")  
   
   
# Python code to illustrate split() function 
with open("file.text", "r") as file: 
    data = file.readlines() 
    for line in data: 
        word = line.split() 
        print word 
