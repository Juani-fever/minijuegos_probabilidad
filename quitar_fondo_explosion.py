
from PIL import Image, ImageSequence

entrada = "assets/images/explosion.gif"
salida = "assets/images/explosion_transparente.gif"

gif = Image.open(entrada)
cuadros = []

for cuadro in ImageSequence.Iterator(gif):
    cuadro = cuadro.convert("RGBA")
    pixeles = cuadro.load()

    for y in range(cuadro.height):
        for x in range(cuadro.width):
            r, g, b, a = pixeles[x, y]

            # Hace transparente el negro y los tonos muy oscuros.
            if r < 25 and g < 25 and b < 25:
                pixeles[x, y] = (0, 0, 0, 0)

    cuadros.append(cuadro.copy())

duraciones = [
    cuadro.info.get("duration", gif.info.get("duration", 100))
    for cuadro in ImageSequence.Iterator(gif)
]

cuadros[0].save(
    salida,
    save_all=True,
    append_images=cuadros[1:],
    duration=duraciones,
    loop=gif.info.get("loop", 0),
    disposal=2,
    transparency=0
)

print("GIF transparente creado:", salida)
