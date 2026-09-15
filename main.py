

#definicion de alfabeto y simbolos aceptados
alfabeto= {"a","b","c"}
simbolos= {"|","*","(",")"}

#validacion de alfabeto
def validacion_alfabeto (expresion_regular):
    for caracter in expresion_regular:
        if caracter not in alfabeto and caracter not in simbolos:
            return False
    return True

#validacion de orden de parentesis
def validacion_parentesis (expresion_regular):
    contador = 0
    for caracter in expresion_regular:
        if caracter == "(":
            contador += 1
        if caracter == ")":
            contador -= 1
        if contador == -1:
           return False
    if contador == 0:
        return True
    return False

expresion_regular = input("Ingrese la expresion regular: ")

#combinacion de funciones
if validacion_alfabeto (expresion_regular) and validacion_parentesis (expresion_regular):
    print("Proceso Exitoso")
else:
    print("Proceso Invalido, ingrese caracteres y simoblos validos")

resultado =validacion_alfabeto(expresion_regular)
print(resultado)

#construccion del AFN con metodo Thompson





