import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")

texto_es = "Necesito información sobre el estado de mi pedido."
texto_en = "I need information about the status of my order."

tokens_es = encoding.encode(texto_es)
tokens_en = encoding.encode(texto_en)

print("TEXTO EN ESPAÑOL")
print(texto_es)
print("Tokens:", tokens_es)
print("Cantidad:", len(tokens_es))

print("\n" + "=" * 50 + "\n")

print("TEXTO EN INGLÉS")
print(texto_en)
print("Tokens:", tokens_en)
print("Cantidad:", len(tokens_en))