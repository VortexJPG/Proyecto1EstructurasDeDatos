import os
import random
import unittest

from cripta.estructuras.tabla_ordenada import ConjuntoOrdenado, TablaOrdenada
from cripta.estructuras.cola import ColaEnlazada
from cripta.estructuras.ordenamiento import ordenar, busqueda_binaria
from cripta.estructuras.lru import CacheAcotada
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.adaptadores.fuente_offline import FuenteOffline


class TestTablaOrdenada(unittest.TestCase):
    def test_basico(self):
        t = TablaOrdenada()
        t.insertar("b", 2)
        t.insertar("a", 1)
        t.insertar("c", 3)
        self.assertEqual(t.obtener("a"), 1)
        self.assertTrue(t.contiene("b"))
        self.assertIsNone(t.obtener("z"))
        self.assertEqual(t.obtener("z", 0), 0)
        t.insertar("b", 20)  # reemplaza
        self.assertEqual(t.obtener("b"), 20)
        self.assertEqual(len(t), 3)
        self.assertTrue(t.eliminar("a"))
        self.assertFalse(t.eliminar("a"))
        self.assertFalse(t.contiene("a"))

    def test_recorre_en_orden_de_clave(self):
        t = TablaOrdenada()
        for clave in (5, 1, 9, 3, 7):
            t.insertar(clave, clave * 10)
        self.assertEqual(list(t.claves()), [1, 3, 5, 7, 9])
        self.assertEqual(list(t.pares()), [(1, 10), (3, 30), (5, 50), (7, 70), (9, 90)])

    def test_clave_de_otro_tipo_no_esta(self):
        t = TablaOrdenada()
        t.insertar("e-1", 1)
        self.assertIsNone(t.obtener(None))
        self.assertFalse(t.contiene(5))
        self.assertFalse(t.eliminar(None))

    def test_borrado_perezoso(self):
        t = TablaOrdenada()
        for clave in ("a", "b", "c"):
            t.insertar(clave, clave)
        t.eliminar("b")  # solo se marca: el arreglo no se corre
        self.assertEqual(len(t._claves), 3)
        self.assertEqual(len(t), 2)
        self.assertEqual(list(t.claves()), ["a", "c"])
        self.assertIsNone(t.obtener("b"))
        t.insertar("b", "otra vez")  # misma casilla
        self.assertEqual(len(t._claves), 3)
        self.assertEqual(t.obtener("b"), "otra vez")
        t.eliminar("b")
        t.insertar("bb", 1)  # cae justo en la casilla borrada: la reutiliza
        self.assertEqual(len(t._claves), 3)
        self.assertEqual(list(t.claves()), ["a", "bb", "c"])

    def test_compacta_cuando_hay_mucha_basura(self):
        t = TablaOrdenada()
        for i in range(100):
            t.insertar(i, i)
        for i in range(80):
            t.eliminar(i)
        self.assertEqual(len(t), 20)
        self.assertLess(len(t._claves), 100)  # se compactó en algún momento
        self.assertEqual(list(t.claves()), list(range(80, 100)))

    def test_al_azar_igual_que_una_lista(self):
        # Referencia: pares (clave, valor) en una lista que se recorre entera.
        # Es lenta pero obviamente correcta.
        azar = random.Random(5)
        ordenada = TablaOrdenada()
        referencia = []

        def posicion(clave):
            for i in range(len(referencia)):
                if referencia[i][0] == clave:
                    return i
            return -1

        for paso in range(5000):
            clave = f"e-{azar.randrange(300)}"
            operacion = azar.randrange(3)
            i = posicion(clave)
            if operacion == 0:
                ordenada.insertar(clave, paso)
                if i >= 0:
                    referencia[i] = (clave, paso)
                else:
                    referencia.append((clave, paso))
            elif operacion == 1:
                self.assertEqual(ordenada.eliminar(clave), i >= 0)
                if i >= 0:
                    referencia.pop(i)
            else:
                self.assertEqual(ordenada.obtener(clave), referencia[i][1] if i >= 0 else None)
            self.assertEqual(len(ordenada), len(referencia))
        claves = list(ordenada.claves())
        for i in range(1, len(claves)):
            self.assertLess(claves[i - 1], claves[i])
        self.assertEqual(len(claves), len(referencia))
        for clave, valor in referencia:
            self.assertEqual(ordenada.obtener(clave), valor)


class TestConjuntoOrdenado(unittest.TestCase):
    def test_agregar(self):
        s = ConjuntoOrdenado()
        self.assertTrue(s.agregar(1))
        self.assertFalse(s.agregar(1))
        self.assertEqual(len(s), 1)


class TestCola(unittest.TestCase):
    def test_fifo(self):
        q = ColaEnlazada()
        q.encolar(1)
        q.encolar(2)
        self.assertEqual(q.desencolar(), 1)
        self.assertEqual(q.desencolar(), 2)
        with self.assertRaises(IndexError):
            q.desencolar()


class TestOrdenamiento(unittest.TestCase):
    def test_estabilidad(self):
        datos = [(1, "b"), (2, "a"), (1, "a")]
        res = ordenar(datos, clave=lambda x: x[0])
        self.assertEqual([x[1] for x in res if x[0] == 1], ["b", "a"])

    def test_binaria(self):
        lista = [1, 3, 5, 7]
        self.assertEqual(busqueda_binaria(lista, 5), 2)
        self.assertEqual(busqueda_binaria(lista, 4), -1)


class TestLRU(unittest.TestCase):
    def test_desalojo_y_fijado(self):
        c = CacheAcotada(2)
        c.insertar("a", 1)
        c.insertar("b", 2)
        c.fijar("a")
        c.insertar("c", 3)
        self.assertTrue(c.contiene("a"))
        self.assertTrue(c.contiene("c"))
        self.assertFalse(c.contiene("b"))


class TestAcciones(unittest.TestCase):
    def test_roundtrip(self):
        for a in [
            Accion(TipoAccion.MOVER, direccion="N"),
            Accion(TipoAccion.ATACAR, objetivo="e-1"),
            Accion(TipoAccion.ESPERAR),
            Accion(TipoAccion.RETROCEDER),
        ]:
            self.assertEqual(Accion.desde_linea(a.a_linea()), a)


class TestOffline(unittest.TestCase):
    def test_parse(self):
        base = os.path.join(os.path.dirname(__file__), "..", "datos_ejemplo", "cripta-01")
        f = FuenteOffline(base)
        self.assertEqual(len(f.catalogo(["itm_antidoto"])), 1)
        cs = f.contenido("cripta-01", [2])[0]
        self.assertEqual(cs.sala, 2)


if __name__ == "__main__":
    unittest.main()
