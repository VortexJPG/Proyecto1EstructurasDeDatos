"""Guardado de la partida en binario propio (y en JSON para comparar). [Persona B]

§4.10. Formato (módulo ``struct``, little-endian):
    [ENCABEZADO]  "CRPT" | versión del formato (u16) | cantidad de salas (u32)
                  | posición del índice (u64)
    [GLOBAL]      largo (u64) + versiones, semilla, azar, reloj, secuencia,
                  jugador, efectos, eventos, objetos_generados
    [SALAS]       un bloque por sala, ordenados por id
    [ÍNDICE]      (id de sala u32, posición u64, largo u32) ordenado por id
Los textos se escriben como largo (u32) + bytes UTF-8.
``cargar_sala`` lee solo el encabezado, el índice (búsqueda binaria) y el
bloque de esa sala, sin leer el archivo completo. Un archivo de otra versión
del formato se rechaza con ``ErrorFormatoIncompatible``.
"""

from __future__ import annotations

import json
import struct
from typing import BinaryIO, Any

from cripta.estructuras.ordenamiento import ordenar, busqueda_binaria
from cripta.modelo.guardable import (
    EstadoGuardable,
    RegistroEfecto,
    RegistroEnemigo,
    RegistroEvento,
    RegistroJugador,
    RegistroObjeto,
    RegistroPuerta,
    RegistroSala,
    RegistroTrampa,
)

MAGIA = b"CRPT"
# 2: se agregó ``objetos_generados`` al bloque global.
VERSION_FORMATO = 2


class ErrorFormatoIncompatible(Exception):
    pass


def _txt(archivo: BinaryIO, texto: str) -> None:
    data = texto.encode("utf-8")
    archivo.write(struct.pack("<I", len(data)))
    archivo.write(data)


def _leer_txt(archivo: BinaryIO) -> str:
    (n,) = struct.unpack("<I", archivo.read(4))
    data = archivo.read(n)
    return data.decode("utf-8")


def _bool_byte(valor: bool) -> bytes:
    return b"\x01" if valor else b"\x00"


class GuardadoBinario:
    def guardar(self, ruta: str, estado: EstadoGuardable) -> None:
        global_bytes = self._codificar_global(estado)
        sala_bloques: list[tuple[int, bytes]] = []
        for sala in estado.salas:
            sala_bloques.append((sala.id, self._codificar_sala(sala)))
        # ordenar bloques por id
        ordenados = ordenar(sala_bloques, clave=lambda x: x[0])
        # calcular offsets
        header_len = 4 + 2 + 4 + 8  # magia, version, cantidad, offset_indice
        offset_global = header_len
        global_prefixed = struct.pack("<Q", len(global_bytes)) + global_bytes
        offset_salas = offset_global + len(global_prefixed)
        # offsets por sala
        entradas_indice = []
        cursor = offset_salas
        for sala_id, bloque in ordenados:
            entradas_indice.append((sala_id, cursor, len(bloque)))
            cursor += len(bloque)
        offset_indice = cursor

        with open(ruta, "wb") as archivo:
            archivo.write(MAGIA)
            archivo.write(struct.pack("<H", VERSION_FORMATO))
            archivo.write(struct.pack("<I", len(ordenados)))
            archivo.write(struct.pack("<Q", offset_indice))
            archivo.write(global_prefixed)
            for sala_id, bloque in ordenados:
                archivo.write(bloque)
            # índice: cantidad + entradas
            archivo.write(struct.pack("<I", len(entradas_indice)))
            for sala_id, off, lng in entradas_indice:
                archivo.write(struct.pack("<IQI", sala_id, off, lng))

    def cargar(self, ruta: str) -> EstadoGuardable:
        with open(ruta, "rb") as archivo:
            magia = archivo.read(4)
            if magia != MAGIA:
                raise ErrorFormatoIncompatible("magia inválida")
            (version,) = struct.unpack("<H", archivo.read(2))
            if version != VERSION_FORMATO:
                raise ErrorFormatoIncompatible(
                    f"versión de formato {version}, se esperaba {VERSION_FORMATO}"
                )
            (cantidad_salas,) = struct.unpack("<I", archivo.read(4))
            (offset_indice,) = struct.unpack("<Q", archivo.read(8))
            # global
            (lng_global,) = struct.unpack("<Q", archivo.read(8))
            datos_global = archivo.read(lng_global)
            estado = self._decodificar_global(datos_global)
            # salas: se cargan todas para reconstruir estado
            salas = []
            # leer bloque de salas entre global y índice
            # necesitamos índice para saber offsets/longs
            archivo.seek(offset_indice)
            (cantidad_indice,) = struct.unpack("<I", archivo.read(4))
            entradas = []
            for _ in range(cantidad_indice):
                sala_id, off, lng = struct.unpack("<IQI", archivo.read(4 + 8 + 4))
                entradas.append((sala_id, off, lng))
            for sala_id, off, lng in entradas:
                archivo.seek(off)
                bloque = archivo.read(lng)
                salas.append(self._decodificar_sala(bloque))
            estado.salas = salas
            return estado

    def cargar_sala(self, ruta: str, sala_id: int) -> RegistroSala | None:
        with open(ruta, "rb") as archivo:
            magia = archivo.read(4)
            if magia != MAGIA:
                raise ErrorFormatoIncompatible("magia inválida")
            (version,) = struct.unpack("<H", archivo.read(2))
            if version != VERSION_FORMATO:
                raise ErrorFormatoIncompatible("versión incompatible")
            archivo.read(4)  # cantidad
            (offset_indice,) = struct.unpack("<Q", archivo.read(8))
            archivo.seek(offset_indice)
            (cantidad_indice,) = struct.unpack("<I", archivo.read(4))
            entradas = []
            for _ in range(cantidad_indice):
                sid, off, lng = struct.unpack("<IQI", archivo.read(4 + 8 + 4))
                entradas.append((sid, off, lng))
            # El índice se escribió ordenado por id: búsqueda binaria (§4.10).
            posicion = busqueda_binaria(entradas, sala_id, clave=lambda entrada: entrada[0])
            if posicion < 0:
                return None
            _, off, lng = entradas[posicion]
            archivo.seek(off)
            return self._decodificar_sala(archivo.read(lng))

    def _codificar_global(self, estado: EstadoGuardable) -> bytes:
        import io

        buf = io.BytesIO()
        _txt(buf, estado.cripta_id)
        _txt(buf, estado.version_cripta)
        _txt(buf, estado.version_catalogo)
        buf.write(struct.pack("<q", estado.semilla))
        # estado_azar como texto JSON
        try:
            import json

            azar_txt = json.dumps(list(estado.estado_azar) if isinstance(estado.estado_azar, (tuple, list)) else estado.estado_azar, default=str)
        except Exception:
            azar_txt = str(estado.estado_azar)
        _txt(buf, azar_txt)
        buf.write(struct.pack("<q", estado.reloj))
        buf.write(struct.pack("<q", estado.siguiente_secuencia))
        # jugador
        j = estado.jugador
        _txt(buf, j.nombre)
        buf.write(struct.pack("<q", j.sala))
        buf.write(struct.pack("<i", j.vida))
        buf.write(struct.pack("<i", j.vida_max))
        buf.write(struct.pack("<i", j.ataque))
        buf.write(struct.pack("<i", j.defensa))
        buf.write(struct.pack("<i", j.velocidad))
        tiemp = -1 if j.tiempo_siguiente is None else j.tiempo_siguiente
        buf.write(struct.pack("<q", tiemp))
        buf.write(struct.pack("<I", len(j.inventario)))
        for obj in j.inventario:
            _txt(buf, obj.instancia)
            _txt(buf, obj.tipo)
        for txt in (j.arma_equipada, j.armadura_equipada):
            _txt(buf, "" if txt is None else txt)
        buf.write(struct.pack("<I", j.acciones_ejecutadas))
        buf.write(struct.pack("<I", j.enemigos_derrotados))
        buf.write(_bool_byte(j.abrio_puerta_salida))
        # efectos
        buf.write(struct.pack("<I", len(estado.efectos)))
        for e in estado.efectos:
            _txt(buf, e.tipo)
            _txt(buf, e.portador)
            buf.write(struct.pack("<q", e.inicio))
            fin = -1 if e.fin is None else e.fin
            buf.write(struct.pack("<q", fin))
            buf.write(struct.pack("<i", e.magnitud))
        # eventos
        buf.write(struct.pack("<I", len(estado.eventos)))
        for ev in estado.eventos:
            buf.write(struct.pack("<q", ev.tiempo))
            buf.write(struct.pack("<q", ev.secuencia))
            _txt(buf, ev.tipo)
            _txt(buf, ev.objetivo)
        buf.write(struct.pack("<q", estado.objetos_generados))
        return buf.getvalue()

    def _decodificar_global(self, datos: bytes) -> EstadoGuardable:
        import io

        buf = io.BytesIO(datos)
        cripta_id = _leer_txt(buf)
        version_cripta = _leer_txt(buf)
        version_catalogo = _leer_txt(buf)
        (semilla,) = struct.unpack("<q", buf.read(8))
        azar_txt = _leer_txt(buf)
        (reloj,) = struct.unpack("<q", buf.read(8))
        (sig_sec,) = struct.unpack("<q", buf.read(8))
        nombre = _leer_txt(buf)
        (sala,) = struct.unpack("<q", buf.read(8))
        (vida,) = struct.unpack("<i", buf.read(4))
        (vida_max,) = struct.unpack("<i", buf.read(4))
        (ataque,) = struct.unpack("<i", buf.read(4))
        (defensa,) = struct.unpack("<i", buf.read(4))
        (velocidad,) = struct.unpack("<i", buf.read(4))
        (tiemp,) = struct.unpack("<q", buf.read(8))
        tiempo_siguiente = None if tiemp < 0 else tiemp
        (cant_inv,) = struct.unpack("<I", buf.read(4))
        inventario = []
        for _ in range(cant_inv):
            instancia = _leer_txt(buf)
            tipo = _leer_txt(buf)
            inventario.append(RegistroObjeto(instancia=instancia, tipo=tipo))
        arma = _leer_txt(buf)
        armadura = _leer_txt(buf)
        (acciones,) = struct.unpack("<I", buf.read(4))
        (derrotados,) = struct.unpack("<I", buf.read(4))
        (abrio_byte,) = struct.unpack("<B", buf.read(1))
        jugador = RegistroJugador(
            nombre=nombre,
            sala=sala,
            vida=vida,
            vida_max=vida_max,
            ataque=ataque,
            defensa=defensa,
            velocidad=velocidad,
            tiempo_siguiente=tiempo_siguiente,
            inventario=inventario,
            arma_equipada=None if arma == "" else arma,
            armadura_equipada=None if armadura == "" else armadura,
            acciones_ejecutadas=acciones,
            enemigos_derrotados=derrotados,
            abrio_puerta_salida=bool(abrio_byte),
        )
        (cant_ef,) = struct.unpack("<I", buf.read(4))
        efectos = []
        for _ in range(cant_ef):
            tipo = _leer_txt(buf)
            portador = _leer_txt(buf)
            (inicio,) = struct.unpack("<q", buf.read(8))
            (fin_raw,) = struct.unpack("<q", buf.read(8))
            fin = None if fin_raw < 0 else fin_raw
            (magnitud,) = struct.unpack("<i", buf.read(4))
            efectos.append(
                RegistroEfecto(tipo=tipo, portador=portador, inicio=inicio, fin=fin, magnitud=magnitud)
            )
        (cant_ev,) = struct.unpack("<I", buf.read(4))
        eventos = []
        for _ in range(cant_ev):
            (tiempo,) = struct.unpack("<q", buf.read(8))
            (secuencia,) = struct.unpack("<q", buf.read(8))
            tipo = _leer_txt(buf)
            objetivo = _leer_txt(buf)
            eventos.append(RegistroEvento(tiempo=tiempo, secuencia=secuencia, tipo=tipo, objetivo=objetivo))
        (objetos_generados,) = struct.unpack("<q", buf.read(8))
        # estado_azar se guarda como texto; intentar parsear JSON a tuple si procede
        try:
            import json

            parsed = json.loads(azar_txt)
            if isinstance(parsed, list):
                estado_azar = tuple(parsed)
            else:
                estado_azar = parsed
        except Exception:
            estado_azar = azar_txt
        return EstadoGuardable(
            cripta_id=cripta_id,
            version_cripta=version_cripta,
            version_catalogo=version_catalogo,
            semilla=semilla,
            estado_azar=estado_azar,
            reloj=reloj,
            siguiente_secuencia=sig_sec,
            jugador=jugador,
            salas=[],
            efectos=efectos,
            eventos=eventos,
            objetos_generados=objetos_generados,
        )

    def _codificar_sala(self, sala: RegistroSala) -> bytes:
        import io

        buf = io.BytesIO()
        buf.write(struct.pack("<q", sala.id))
        # rastro optional
        rastro = -1 if sala.rastro is None else sala.rastro
        buf.write(struct.pack("<q", rastro))
        buf.write(_bool_byte(sala.contenido_cargado))
        buf.write(_bool_byte(sala.visitada))
        # objetos suelo
        buf.write(struct.pack("<I", len(sala.objetos_suelo)))
        for o in sala.objetos_suelo:
            _txt(buf, o.instancia)
            _txt(buf, o.tipo)
        # trampas
        buf.write(struct.pack("<I", len(sala.trampas)))
        for t in sala.trampas:
            _txt(buf, t.instancia)
            _txt(buf, t.tipo)
            buf.write(_bool_byte(t.armada))
        # enemigos
        buf.write(struct.pack("<I", len(sala.enemigos)))
        for e in sala.enemigos:
            _txt(buf, e.instancia)
            _txt(buf, e.tipo)
            buf.write(struct.pack("<i", e.numero))
            buf.write(struct.pack("<i", e.vida))
            buf.write(_bool_byte(e.activo))
            ts = -1 if e.tiempo_siguiente is None else e.tiempo_siguiente
            buf.write(struct.pack("<q", ts))
        # puertas
        buf.write(struct.pack("<I", len(sala.puertas)))
        for p in sala.puertas:
            _txt(buf, p.direccion)
            buf.write(_bool_byte(p.cerrada))
        return buf.getvalue()

    def _decodificar_sala(self, datos: bytes) -> RegistroSala:
        import io

        buf = io.BytesIO(datos)
        (sala_id,) = struct.unpack("<q", buf.read(8))
        (rastro_raw,) = struct.unpack("<q", buf.read(8))
        rastro = None if rastro_raw < 0 else rastro_raw
        (cc_byte,) = struct.unpack("<B", buf.read(1))
        (vis_byte,) = struct.unpack("<B", buf.read(1))
        (cant_obj,) = struct.unpack("<I", buf.read(4))
        objetos = []
        for _ in range(cant_obj):
            inst = _leer_txt(buf)
            tipo = _leer_txt(buf)
            objetos.append(RegistroObjeto(instancia=inst, tipo=tipo))
        (cant_tr,) = struct.unpack("<I", buf.read(4))
        trampas = []
        for _ in range(cant_tr):
            inst = _leer_txt(buf)
            tipo = _leer_txt(buf)
            (arm,) = struct.unpack("<B", buf.read(1))
            trampas.append(RegistroTrampa(instancia=inst, tipo=tipo, armada=bool(arm)))
        (cant_en,) = struct.unpack("<I", buf.read(4))
        enemigos = []
        for _ in range(cant_en):
            inst = _leer_txt(buf)
            tipo = _leer_txt(buf)
            (numero,) = struct.unpack("<i", buf.read(4))
            (vida,) = struct.unpack("<i", buf.read(4))
            (act,) = struct.unpack("<B", buf.read(1))
            (ts_raw,) = struct.unpack("<q", buf.read(8))
            ts = None if ts_raw < 0 else ts_raw
            enemigos.append(
                RegistroEnemigo(
                    instancia=inst,
                    tipo=tipo,
                    numero=numero,
                    vida=vida,
                    activo=bool(act),
                    tiempo_siguiente=ts,
                )
            )
        (cant_pu,) = struct.unpack("<I", buf.read(4))
        puertas = []
        for _ in range(cant_pu):
            dirr = _leer_txt(buf)
            (cerr,) = struct.unpack("<B", buf.read(1))
            puertas.append(RegistroPuerta(direccion=dirr, cerrada=bool(cerr)))
        return RegistroSala(
            id=sala_id,
            rastro=rastro,
            contenido_cargado=bool(cc_byte),
            visitada=bool(vis_byte),
            objetos_suelo=objetos,
            trampas=trampas,
            enemigos=enemigos,
            puertas=puertas,
        )


class GuardadoJSON:
    def guardar(self, ruta: str, estado: EstadoGuardable) -> None:
        payload = self._a_dict(estado)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def cargar(self, ruta: str) -> EstadoGuardable:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return self._desde_dict(datos)

    def _a_dict(self, estado: EstadoGuardable) -> dict[str, Any]:
        return {
            "cripta_id": estado.cripta_id,
            "version_cripta": estado.version_cripta,
            "version_catalogo": estado.version_catalogo,
            "semilla": estado.semilla,
            "estado_azar": list(estado.estado_azar)
            if isinstance(estado.estado_azar, (tuple, list))
            else estado.estado_azar,
            "reloj": estado.reloj,
            "siguiente_secuencia": estado.siguiente_secuencia,
            "jugador": {
                "nombre": estado.jugador.nombre,
                "sala": estado.jugador.sala,
                "vida": estado.jugador.vida,
                "vida_max": estado.jugador.vida_max,
                "ataque": estado.jugador.ataque,
                "defensa": estado.jugador.defensa,
                "velocidad": estado.jugador.velocidad,
                "tiempo_siguiente": estado.jugador.tiempo_siguiente,
                "inventario": [
                    {"instancia": o.instancia, "tipo": o.tipo} for o in estado.jugador.inventario
                ],
                "arma_equipada": estado.jugador.arma_equipada,
                "armadura_equipada": estado.jugador.armadura_equipada,
                "acciones_ejecutadas": estado.jugador.acciones_ejecutadas,
                "enemigos_derrotados": estado.jugador.enemigos_derrotados,
                "abrio_puerta_salida": estado.jugador.abrio_puerta_salida,
            },
            "salas": [
                {
                    "id": s.id,
                    "rastro": s.rastro,
                    "contenido_cargado": s.contenido_cargado,
                    "visitada": s.visitada,
                    "objetos_suelo": [{"instancia": o.instancia, "tipo": o.tipo} for o in s.objetos_suelo],
                    "trampas": [{"instancia": t.instancia, "tipo": t.tipo, "armada": t.armada} for t in s.trampas],
                    "enemigos": [
                        {
                            "instancia": e.instancia,
                            "tipo": e.tipo,
                            "numero": e.numero,
                            "vida": e.vida,
                            "activo": e.activo,
                            "tiempo_siguiente": e.tiempo_siguiente,
                        }
                        for e in s.enemigos
                    ],
                    "puertas": [{"direccion": p.direccion, "cerrada": p.cerrada} for p in s.puertas],
                }
                for s in estado.salas
            ],
            "efectos": [
                {
                    "tipo": e.tipo,
                    "portador": e.portador,
                    "inicio": e.inicio,
                    "fin": e.fin,
                    "magnitud": e.magnitud,
                }
                for e in estado.efectos
            ],
            "eventos": [
                {
                    "tiempo": ev.tiempo,
                    "secuencia": ev.secuencia,
                    "tipo": ev.tipo,
                    "objetivo": ev.objetivo,
                }
                for ev in estado.eventos
            ],
            "objetos_generados": estado.objetos_generados,
        }

    def _desde_dict(self, d: dict[str, Any]) -> EstadoGuardable:
        j = d["jugador"]
        jugador = RegistroJugador(
            nombre=j["nombre"],
            sala=j["sala"],
            vida=j["vida"],
            vida_max=j["vida_max"],
            ataque=j["ataque"],
            defensa=j["defensa"],
            velocidad=j["velocidad"],
            tiempo_siguiente=j.get("tiempo_siguiente"),
            inventario=[RegistroObjeto(instancia=o["instancia"], tipo=o["tipo"]) for o in j.get("inventario", [])],
            arma_equipada=j.get("arma_equipada"),
            armadura_equipada=j.get("armadura_equipada"),
            acciones_ejecutadas=j.get("acciones_ejecutadas", 0),
            enemigos_derrotados=j.get("enemigos_derrotados", 0),
            abrio_puerta_salida=j.get("abrio_puerta_salida", False),
        )
        salas = []
        for s in d.get("salas", []):
            salas.append(
                RegistroSala(
                    id=s["id"],
                    rastro=s.get("rastro"),
                    contenido_cargado=s.get("contenido_cargado", False),
                    visitada=s.get("visitada", False),
                    objetos_suelo=[RegistroObjeto(instancia=o["instancia"], tipo=o["tipo"]) for o in s.get("objetos_suelo", [])],
                    trampas=[RegistroTrampa(instancia=t["instancia"], tipo=t["tipo"], armada=t.get("armada", True)) for t in s.get("trampas", [])],
                    enemigos=[
                        RegistroEnemigo(
                            instancia=e["instancia"],
                            tipo=e["tipo"],
                            numero=e.get("numero", 1),
                            vida=e.get("vida", 0),
                            activo=e.get("activo", False),
                            tiempo_siguiente=e.get("tiempo_siguiente"),
                        )
                        for e in s.get("enemigos", [])
                    ],
                    puertas=[RegistroPuerta(direccion=p["direccion"], cerrada=p.get("cerrada", False)) for p in s.get("puertas", [])],
                )
            )
        efectos = [
            RegistroEfecto(
                tipo=e["tipo"],
                portador=e["portador"],
                inicio=e["inicio"],
                fin=e.get("fin"),
                magnitud=e.get("magnitud", 0),
            )
            for e in d.get("efectos", [])
        ]
        eventos = [
            RegistroEvento(
                tiempo=ev["tiempo"],
                secuencia=ev["secuencia"],
                tipo=ev["tipo"],
                objetivo=ev["objetivo"],
            )
            for ev in d.get("eventos", [])
        ]
        azar = d.get("estado_azar")
        if isinstance(azar, list):
            azar = tuple(azar)
        return EstadoGuardable(
            cripta_id=d["cripta_id"],
            version_cripta=d["version_cripta"],
            version_catalogo=d["version_catalogo"],
            semilla=d["semilla"],
            estado_azar=azar,
            reloj=d["reloj"],
            siguiente_secuencia=d["siguiente_secuencia"],
            jugador=jugador,
            salas=salas,
            efectos=efectos,
            eventos=eventos,
            objetos_generados=d.get("objetos_generados", 0),
        )
