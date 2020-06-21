def getKey(key):
    with open('ApiKeys.txt') as file:
        file_contents = file.read()
        lines = file_contents.split("\n")    
        for i in lines:
            if (key in i):
                return(i.split("=")[1])
        
        
