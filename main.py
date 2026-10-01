import re
import urllib.parse

from flask import Flask, request, jsonify, render_template
from graphviz import Digraph

app = Flask(__name__)

alfabeto = {"a", "b", "c"}
simbolos = {"|", "*", "(", ")"}

def validacion_alfabeto(expresion_regular):
    for caracter in expresion_regular:
        if caracter not in alfabeto and caracter not in simbolos:
            return False
    return True

def validacion_parentesis(expresion_regular):
    contador = 0
    for caracter in expresion_regular:
        if caracter == "(":
            contador += 1
        if caracter == ")":
            contador -= 1
        if contador == -1:
            return False
    return contador == 0

def validacion_estructura(expresion_regular):
    # Rechaza operadores mal colocados:
    # empieza con | o *, "||", "(|", "|)", "|*", "(*", "**", "()" o termina en |
    patrones = [r"^[|*]", r"[|(]\|", r"\|\)", r"\|\*", r"\(\*", r"\*\*", r"\(\)", r"\|$"]
    return not any(re.search(p, expresion_regular) for p in patrones)

def construir_automata(expresion_regular):
    contador_estados = [0]
    transiciones = []

    def nuevo_estado():
        estado = contador_estados[0]
        contador_estados[0] += 1
        return estado

    def construir_simbolo(simbolo):
        inicio = nuevo_estado()
        fin = nuevo_estado()
        transiciones.append((inicio, simbolo, fin))
        return inicio, fin

    def concatenar(inicio_a, fin_a, inicio_b, fin_b):
        transiciones.append((fin_a, "epsilon", inicio_b))
        return inicio_a, fin_b

    def union(inicio_a, fin_a, inicio_b, fin_b):
        inicio_nuevo = nuevo_estado()
        fin_nuevo = nuevo_estado()
        transiciones.append((inicio_nuevo, "epsilon", inicio_a))
        transiciones.append((inicio_nuevo, "epsilon", inicio_b))
        transiciones.append((fin_a, "epsilon", fin_nuevo))
        transiciones.append((fin_b, "epsilon", fin_nuevo))
        return inicio_nuevo, fin_nuevo

    def cerradura(inicio_a, fin_a):
        inicio_nuevo = nuevo_estado()
        fin_nuevo = nuevo_estado()
        transiciones.append((inicio_nuevo, "epsilon", inicio_a))
        transiciones.append((inicio_nuevo, "epsilon", fin_nuevo))
        transiciones.append((fin_a, "epsilon", inicio_a))
        transiciones.append((fin_a, "epsilon", fin_nuevo))
        return inicio_nuevo, fin_nuevo

    posicion = [0]

    def parsear_elemento():
        if expresion_regular[posicion[0]] == "(":
            posicion[0] += 1
            inicio, fin = parsear_union()
            posicion[0] += 1
            return inicio, fin
        caracter_actual = expresion_regular[posicion[0]]
        posicion[0] += 1
        return construir_simbolo(caracter_actual)

    def parsear_cerradura():
        inicio, fin = parsear_elemento()
        if posicion[0] < len(expresion_regular) and expresion_regular[posicion[0]] == "*":
            posicion[0] += 1
            inicio, fin = cerradura(inicio, fin)
        return inicio, fin

    def parsear_concatenacion():
        inicio, fin = parsear_cerradura()
        while posicion[0] < len(expresion_regular) and (
            expresion_regular[posicion[0]] in alfabeto or expresion_regular[posicion[0]] == "("
        ):
            inicio2, fin2 = parsear_cerradura()
            inicio, fin = concatenar(inicio, fin, inicio2, fin2)
        return inicio, fin

    def parsear_union():
        inicio, fin = parsear_concatenacion()
        while posicion[0] < len(expresion_regular) and expresion_regular[posicion[0]] == "|":
            posicion[0] += 1
            inicio2, fin2 = parsear_concatenacion()
            inicio, fin = union(inicio, fin, inicio2, fin2)
        return inicio, fin

    inicio_final, fin_final = parsear_union()

    def epsilon(estados_iniciales):
        resultado = set(estados_iniciales)
        cambio = True
        while cambio:
            cambio = False
            for origen, simbolo, destino in transiciones:
                if origen in resultado and simbolo == "epsilon" and destino not in resultado:
                    resultado.add(destino)
                    cambio = True
        return resultado

    def mover(estados, simbolo):
        resultado = set()
        for origen, simb, destino in transiciones:
            if origen in estados and simb == simbolo:
                resultado.add(destino)
        return resultado

    estado_inicial_afd = epsilon({inicio_final})
    pendientes = [estado_inicial_afd]
    conocidos = {frozenset(estado_inicial_afd)}
    transiciones_afd = []

    while pendientes:
        actual = pendientes.pop()
        for simbolo in alfabeto:
            nuevo_conjunto = epsilon(mover(actual, simbolo))
            if nuevo_conjunto and frozenset(nuevo_conjunto) not in conocidos:
                conocidos.add(frozenset(nuevo_conjunto))
                pendientes.append(nuevo_conjunto)
            if nuevo_conjunto:
                transiciones_afd.append((frozenset(actual), simbolo, frozenset(nuevo_conjunto)))

    def es_aceptacion(conjunto):
        return fin_final in conjunto

    return {
        "transiciones": transiciones,
        "inicio_final": inicio_final,
        "fin_final": fin_final,
        "estado_inicial_afd": frozenset(estado_inicial_afd),
        "transiciones_afd": transiciones_afd,
        "es_aceptacion": es_aceptacion,
    }

def nombrar_estados_afd(resultado_automata):
    """Asigna un nombre corto (q0, q1, q2...) a cada conjunto de estados del AFD."""
    inicial = resultado_automata["estado_inicial_afd"]
    conjuntos = {inicial}
    for origen, simbolo, destino in resultado_automata["transiciones_afd"]:
        conjuntos.add(origen)
        conjuntos.add(destino)

    nombres = {inicial: "q0"}
    otros = sorted(conjuntos - {inicial}, key=lambda c: sorted(c))
    for indice, conjunto in enumerate(otros, start=1):
        nombres[conjunto] = f"q{indice}"
    return nombres

def describir_afd(resultado_automata):
    """Describe el AFD con una estructura común, para dibujarlo,
    simularlo y armar su tabla."""
    nombres = nombrar_estados_afd(resultado_automata)
    return {
        "nombres": nombres,
        "inicial": resultado_automata["estado_inicial_afd"],
        "finales": {c for c in nombres if resultado_automata["es_aceptacion"](c)},
        "transiciones": resultado_automata["transiciones_afd"],
        "detalle": {c: "{" + ",".join(str(e) for e in sorted(c)) + "}" for c in nombres},
    }

def simular_afd(cadena, afd):
    """Simula una cadena en el AFD."""
    nombres = afd["nombres"]
    estado_actual = afd["inicial"]
    camino = [{"estado": nombres[estado_actual], "simbolo": None}]

    for caracter in cadena:
        siguiente = None
        for origen, simbolo, destino in afd["transiciones"]:
            if origen == estado_actual and simbolo == caracter:
                siguiente = destino
                break
        if siguiente is None:
            camino.append({"estado": None, "simbolo": caracter})
            return False, camino
        estado_actual = siguiente
        camino.append({"estado": nombres[estado_actual], "simbolo": caracter})

    return estado_actual in afd["finales"], camino

def cerradura_epsilon(estados, transiciones):
    resultado = set(estados)
    pendientes = list(estados)
    while pendientes:
        actual = pendientes.pop()
        for origen, simbolo, destino in transiciones:
            if origen == actual and simbolo == "epsilon" and destino not in resultado:
                resultado.add(destino)
                pendientes.append(destino)
    return resultado

def mover_afn(estados, simbolo_leido, transiciones):
    return {destino for origen, simbolo, destino in transiciones
            if origen in estados and simbolo == simbolo_leido}

def formato_conjunto(conjunto):
    return "{" + ",".join(str(e) for e in sorted(conjunto)) + "}"

def simular_afn(cadena, resultado_automata):
    transiciones = resultado_automata["transiciones"]
    actuales = cerradura_epsilon({resultado_automata["inicio_final"]}, transiciones)
    camino = [{"estado": formato_conjunto(actuales), "simbolo": None}]

    for caracter in cadena:
        siguientes = cerradura_epsilon(mover_afn(actuales, caracter, transiciones), transiciones)
        if not siguientes:
            camino.append({"estado": None, "simbolo": caracter})
            return False, camino
        actuales = siguientes
        camino.append({"estado": formato_conjunto(actuales), "simbolo": caracter})

    return resultado_automata["fin_final"] in actuales, camino

def armar_tabla(afd):
    simbolos_ordenados = sorted(alfabeto)
    filas = []
    for estado, nombre in sorted(afd["nombres"].items(), key=lambda p: int(p[1][1:])):
        destinos = {s: "-" for s in simbolos_ordenados}
        for origen, simbolo, dest in afd["transiciones"]:
            if origen == estado:
                destinos[simbolo] = afd["nombres"][dest]
        filas.append({
            "estado": nombre,
            "detalle": afd["detalle"][estado],
            "inicial": estado == afd["inicial"],
            "final": estado in afd["finales"],
            "destinos": destinos,
        })
    return {"simbolos": simbolos_ordenados, "filas": filas}

def generar_diagrama_afn(resultado_automata):
    """Genera la URL del diagrama AFN usando la API de QuickChart."""
    grafo = Digraph()
    grafo.attr(rankdir="LR", bgcolor="white")
    grafo.attr("node", fontname="Helvetica", fontsize="12", color="#4f46e5", fontcolor="#1f2937")
    grafo.attr("edge", fontname="Helvetica", fontsize="11", color="#6b7280", fontcolor="#1f2937")

    grafo.node(str(resultado_automata["inicio_final"]), shape="circle", style="filled", fillcolor="#eef2ff")
    grafo.node(str(resultado_automata["fin_final"]), shape="doublecircle", style="filled", fillcolor="#d1fae5")
    for origen, simbolo, destino in resultado_automata["transiciones"]:
        grafo.edge(str(origen), str(destino), label="ε" if simbolo == "epsilon" else str(simbolo))

    # Obtenemos el código DOT en texto y creamos la URL para QuickChart
    codigo_dot = grafo.source
    return f"https://quickchart.io/graphviz?graph={urllib.parse.quote(codigo_dot)}"

def dibujar_afd(afd):
    """Genera la URL del diagrama AFD usando la API de QuickChart."""
    grafo = Digraph()
    grafo.attr(rankdir="LR", bgcolor="white")
    grafo.attr("node", fontname="Helvetica", fontsize="11", color="#4f46e5", fontcolor="#1f2937")
    grafo.attr("edge", fontname="Helvetica", fontsize="11", color="#6b7280", fontcolor="#1f2937")

    for estado, nombre in afd["nombres"].items():
        es_final = estado in afd["finales"]
        grafo.node(
            nombre,
            label=f"{nombre}\n{afd['detalle'][estado]}",
            shape="doublecircle" if es_final else "circle",
            style="filled",
            fillcolor="#d1fae5" if es_final else "#eef2ff",
        )

    # Flecha de entrada al estado inicial
    grafo.node("inicio", shape="point", width="0.1")
    grafo.edge("inicio", afd["nombres"][afd["inicial"]])

    etiquetas = {}
    for origen, simbolo, dest in afd["transiciones"]:
        etiquetas.setdefault((origen, dest), []).append(simbolo)
    for (origen, dest), lista in etiquetas.items():
        grafo.edge(afd["nombres"][origen], afd["nombres"][dest], label=",".join(sorted(lista)))

    # Obtenemos el código DOT en texto y creamos la URL para QuickChart
    codigo_dot = grafo.source
    return f"https://quickchart.io/graphviz?graph={urllib.parse.quote(codigo_dot)}"

ultimo_resultado = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generar", methods=["POST"])
def generar():
    global ultimo_resultado
    datos = request.get_json()
    er = datos.get("er", "")

    if (not er or not validacion_alfabeto(er) or not validacion_parentesis(er)
            or not validacion_estructura(er)):
        return jsonify({"valido": False, "mensaje": "ER inválida: revisa símbolos, paréntesis u operadores"})

    resultado = construir_automata(er)
    ultimo_resultado = resultado

    afd = describir_afd(resultado)

    # Generamos las URLs en lugar de archivos físicos en disco
    url_afn = generar_diagrama_afn(resultado)
    url_afd = dibujar_afd(afd)

    return jsonify({
        "valido": True,
        "imagen_afn": url_afn,
        "imagen_afd": url_afd,
        "tabla_afd": armar_tabla(afd),
    })

@app.route("/probar", methods=["POST"])
def probar():
    datos = request.get_json()
    cadena = datos.get("cadena", "")
    tipo = datos.get("automata", "afd")

    if not ultimo_resultado:
        return jsonify({"pertenece": False, "mensaje": "Primero genera un autómata"})

    if tipo == "afn":
        pertenece, camino = simular_afn(cadena, ultimo_resultado)
    else:
        tipo = "afd"
        pertenece, camino = simular_afd(cadena, describir_afd(ultimo_resultado))

    return jsonify({"pertenece": pertenece, "camino": camino, "automata": tipo})

if __name__ == "__main__":
    app.run(debug=True)