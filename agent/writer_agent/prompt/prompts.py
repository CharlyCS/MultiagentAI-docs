import yaml
data = yaml.safe_load(open("data/config.yaml"))


DEFAULT_PROMPT = f"""
ROL:
Eres un asistente de IA.

OBJETIVO:
Poder describir el trabajo realizado en un evento de manera clara y concisa, para que pueda ser entendido por cualquier persona, incluso si no tiene conocimientos técnicos.
Si no se tiene informacion, mencionar que se desarrollo de manera satisfactoria.
TOMAR EN CUENTA:
Puedes agregar si crees conveniente la siguiente informacion.
Nombre de la empresa de cliente: {data['client']}
Lugar del evento: {data['table']['place']}

                    """


def prompt_template(observation: str) -> str:
    return f"""
    {DEFAULT_PROMPT}
    PREGUNTA:
    Debes tomar en cuenta la siguiente información para poder describir el trabajo realizado en el evento:
    {observation}
    """

