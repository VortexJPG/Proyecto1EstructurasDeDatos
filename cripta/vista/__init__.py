"""Vista (MVC, §6).                                                  [Persona A]

Solo presenta el estado y recoge lo que hace el usuario. Nunca modifica el
modelo directamente: entrega ``ComandoUsuario`` al controlador.

Hay dos vistas intercambiables con los mismos métodos: la consola
(``vista_consola``, la de siempre) y la ventana con sprites
(``vista_grafica``, con ``--gui``). Lo que comparten está en ``base``.
"""
