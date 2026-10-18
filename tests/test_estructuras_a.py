"""Pruebas de las estructuras de Persona A: MonticuloMin, ListaDoble (no circular), BufferCircular.

No dependen de nada de Persona B.
"""

import random
import unittest

from cripta.constantes import indice_direccion
from cripta.estructuras.buffer_circular import BufferCircular
from cripta.estructuras.lista_doble import ListaDoble
from cripta.estructuras.monticulo import MonticuloMin


class PruebaMonticulo(unittest.TestCase):
    def test_extrae_en_orden(self):
        azar = random.Random(7)
        monticulo = MonticuloMin()
        valores = [azar.randint(0, 1000) for _ in range(500)]
        for valor in valores:
            monticulo.insertar(valor)
        extraidos = [monticulo.extraer_min() for _ in range(len(valores))]
        for i in range(1, len(extraidos)):
            self.assertLessEqual(extraidos[i - 1], extraidos[i])
        self.assertTrue(monticulo.esta_vacio())

    def test_ver_min_y_vacio(self):
        monticulo = MonticuloMin()
        self.assertIsNone(monticulo.ver_min())
        with self.assertRaises(IndexError):
            monticulo.extraer_min()
        monticulo.insertar(5)
        monticulo.insertar(2)
        self.assertEqual(monticulo.ver_min(), 2)
        self.assertEqual(len(monticulo), 2)

    def test_empates_por_secuencia(self):
        # Tuplas (tiempo, secuencia): mismo tiempo → menor secuencia primero.
        monticulo = MonticuloMin()
        for secuencia in (3, 1, 2, 0):
            monticulo.insertar((100, secuencia))
        self.assertEqual([monticulo.extraer_min() for _ in range(4)], [(100, 0), (100, 1), (100, 2), (100, 3)])

    def test_reconstruir(self):
        monticulo = MonticuloMin()
        monticulo.reconstruir([9, 4, 7, 1, 8, 2])
        self.assertEqual([monticulo.extraer_min() for _ in range(6)], [1, 2, 4, 7, 8, 9])


class PruebaListaDoble(unittest.TestCase):
    def test_agregar_y_recorrer(self):
        lista = ListaDoble()
        lista.agregar_al_final(2)
        lista.agregar_al_final(3)
        lista.agregar_al_frente(1)
        self.assertEqual(list(lista), [1, 2, 3])
        self.assertEqual(list(lista.iterar_reversa()), [3, 2, 1])
        self.assertEqual(len(lista), 3)
        self.assertEqual(lista.primero.valor, 1)
        self.assertEqual(lista.ultimo.valor, 3)

    def test_quitar_en_cualquier_posicion(self):
        lista = ListaDoble()
        nodos = [lista.agregar_al_final(i) for i in range(5)]
        self.assertEqual(lista.quitar(nodos[2]), 2)
        self.assertEqual(lista.quitar(nodos[0]), 0)
        self.assertEqual(lista.quitar(nodos[4]), 4)
        self.assertEqual(lista.a_lista(), [1, 3])
        self.assertFalse(ListaDoble.esta_enlazado(nodos[2]))
        with self.assertRaises(ValueError):
            lista.quitar(nodos[2])

    def test_mover(self):
        lista = ListaDoble()
        nodos = [lista.agregar_al_final(i) for i in range(4)]
        lista.mover_al_frente(nodos[3])
        self.assertEqual(lista.a_lista(), [3, 0, 1, 2])
        lista.mover_al_final(nodos[3])
        self.assertEqual(lista.a_lista(), [0, 1, 2, 3])
        lista.mover_despues(nodos[0], nodos[2])
        self.assertEqual(lista.a_lista(), [1, 2, 0, 3])

    def test_reenlazar_mismo_nodo(self):
        lista = ListaDoble()
        a, b, c = lista.agregar_al_final("a"), lista.agregar_al_final("b"), lista.agregar_al_final("c")
        anterior = lista.anterior(b)
        lista.quitar(b)
        lista.reenlazar_despues(anterior, b)
        self.assertEqual(lista.a_lista(), ["a", "b", "c"])
        lista.quitar(a)
        lista.reenlazar_despues(None, a)
        self.assertEqual(lista.a_lista(), ["a", "b", "c"])
        self.assertIs(lista.siguiente(c), None)
        self.assertIs(lista.anterior(a), None)

    def test_insertar_despues(self):
        lista = ListaDoble()
        a = lista.agregar_al_final("a")
        lista.agregar_al_final("c")
        lista.insertar_despues(a, "b")
        lista.insertar_despues(None, "inicio")
        self.assertEqual(lista.a_lista(), ["inicio", "a", "b", "c"])

    def test_no_es_circular(self):
        # La lista "de libro": el primero no tiene anterior y el último no tiene siguiente.
        lista = ListaDoble()
        self.assertIsNone(lista.primero)
        self.assertIsNone(lista.ultimo)
        solo = lista.agregar_al_final("solo")
        self.assertIs(lista.primero, solo)
        self.assertIs(lista.ultimo, solo)
        self.assertIsNone(solo.anterior)
        self.assertIsNone(solo.siguiente)
        lista.agregar_al_final("otro")
        self.assertIsNone(lista.primero.anterior)
        self.assertIsNone(lista.ultimo.siguiente)
        lista.quitar(solo)
        lista.quitar(lista.primero)
        self.assertIsNone(lista.primero)
        self.assertIsNone(lista.ultimo)
        self.assertTrue(lista.esta_vacia())

    def test_nodo_de_otra_lista(self):
        una, otra = ListaDoble(), ListaDoble()
        nodo = una.agregar_al_final(1)
        self.assertTrue(una.contiene_nodo(nodo))
        self.assertFalse(otra.contiene_nodo(nodo))
        with self.assertRaises(ValueError):
            otra.quitar(nodo)
        with self.assertRaises(ValueError):
            otra.insertar_despues(nodo, 2)
        self.assertEqual(una.a_lista(), [1])

    def test_operaciones_al_azar(self):
        # Se compara contra una list de Python haciendo lo mismo.
        azar = random.Random(3)
        lista = ListaDoble()
        nodos = []
        esperado = []
        for paso in range(3000):
            operacion = azar.randrange(5)
            if operacion == 0 or not nodos:
                nodos.append(lista.agregar_al_final(paso))
                esperado.append(paso)
            elif operacion == 1:
                nodos.insert(0, lista.agregar_al_frente(paso))
                esperado.insert(0, paso)
            elif operacion == 2:
                i = azar.randrange(len(nodos))
                lista.quitar(nodos.pop(i))
                esperado.pop(i)
            elif operacion == 3:
                i = azar.randrange(len(nodos))
                lista.mover_al_frente(nodos[i])
                nodos.insert(0, nodos.pop(i))
                esperado.insert(0, esperado.pop(i))
            else:
                i = azar.randrange(len(nodos))
                nodo = nodos.pop(i)
                valor = esperado.pop(i)
                j = azar.randrange(len(nodos) + 1)  # j = 0: al frente
                lista.mover_despues(nodo, nodos[j - 1] if j > 0 else None)
                nodos.insert(j, nodo)
                esperado.insert(j, valor)
            self.assertEqual(lista.a_lista(), esperado)
            self.assertEqual(list(lista.iterar_reversa()), esperado[::-1])
            self.assertEqual(len(lista), len(esperado))


class PruebaBufferCircular(unittest.TestCase):
    def test_sobrescribe_el_mas_antiguo(self):
        buffer = BufferCircular(3)
        for i in range(3):
            self.assertIsNone(buffer.agregar(i))
        self.assertTrue(buffer.esta_lleno())
        self.assertEqual(buffer.agregar(3), 0)
        self.assertEqual(list(buffer), [1, 2, 3])
        self.assertEqual(buffer.capacidad, 3)

    def test_pila_acotada(self):
        buffer = BufferCircular(5)
        for i in range(8):
            buffer.agregar(i)
        self.assertEqual([buffer.extraer_reciente() for _ in range(5)], [7, 6, 5, 4, 3])
        self.assertIsNone(buffer.extraer_reciente())
        self.assertTrue(buffer.esta_vacio())

    def test_memoria_constante(self):
        buffer = BufferCircular(20)
        for i in range(10_000):
            buffer.agregar(i)
        self.assertEqual(len(buffer), 20)
        self.assertEqual(len(buffer._ranuras), 20)
        self.assertEqual(list(buffer)[0], 9_980)


class PruebaConstantes(unittest.TestCase):
    def test_indice_direccion(self):
        self.assertEqual([indice_direccion(d) for d in "NSEO"], [0, 1, 2, 3])
        with self.assertRaises(ValueError):
            indice_direccion("X")


if __name__ == "__main__":
    unittest.main()
