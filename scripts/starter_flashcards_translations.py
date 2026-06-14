"""
Tradução curada (pt-BR) dos cards do Starter.

Cada entrada é (front em inglês, lesson_code, tradução). Cards que NÃO
estão neste fixture são descartados como ruído da extração automática.

O `build_flashcards.py` usa esta lista quando existe.
"""

STARTER_CARDS = [
    # File 1 — Introductions, countries
    ("1A", "Nice to meet you",       "Prazer em conhecê-lo(a)."),
    ("1A", "Two cappuccinos, please","Dois cappuccinos, por favor."),
    ("1A", "Sorry",                  "Desculpe / Sinto muito."),
    ("1A", "See you tomorrow",       "Até amanhã."),
    ("1A", "Thanks",                 "Obrigado(a)."),
    ("1A", "What's your name?",      "Qual é o seu nome?"),
    ("1B", "I don't know",           "Eu não sei."),
    ("1B", "I think she's from",     "Acho que ela é de..."),
    ("1B", "Spain",                  "Espanha."),
    ("1B", "It's a nice city",       "É uma cidade legal."),
    ("1B", "Where's",                "Onde está / Onde fica..."),
    ("1B", "Lima",                   "Lima (capital do Peru)."),

    # File 2 — Personal info, numbers
    ("2B", "What's your phone number?","Qual é o seu telefone?"),
    ("2B", "How old are you?",       "Quantos anos você tem?"),
    ("2B", "I'm twenty-five",        "Eu tenho 25 anos."),
    ("2B", "What's your email?",     "Qual é o seu email?"),

    # File 3 — Things in your bag, demonstratives
    ("3A", "What are they?",         "O que são (essas coisas)?"),
    ("3A", "What's in your bag?",    "O que tem na sua bolsa?"),
    ("3A", "Where are my glasses?",  "Onde estão meus óculos?"),
    ("3A", "keys",                   "chaves."),
    ("3A", "wallet",                 "carteira."),

    # File 4 — Family, colors, adjectives
    ("4A", "Be good",                "Seja bonzinho / comporte-se."),
    ("4A", "Let's order pizza",      "Vamos pedir pizza."),
    ("4A", "on the table",           "na mesa."),
    ("4A", "What a nice card",       "Que cartão legal!"),
    ("4B", "Come with me",           "Venha comigo."),
    ("4B", "easy to park",           "fácil de estacionar."),
    ("4B", "I love it",              "Eu amo isso."),
    ("4B", "in my opinion",          "na minha opinião."),
    ("4B", "It's my birthday",       "É meu aniversário."),
    ("4B", "It's small",             "É pequeno."),

    # File 5 — Food, simple present, plane
    ("5A", "I don't eat breakfast",  "Eu não tomo café da manhã."),
    ("5A", "in the morning",         "de manhã."),
    ("5A", "I'm hungry",             "Estou com fome."),
    ("5A", "I'm thirsty",            "Estou com sede."),
    ("5B", "keep the change",        "fique com o troco."),
    ("5B", "What time do we arrive?","Que horas a gente chega?"),
    ("5B", "Do you want fish or pasta?","Você quer peixe ou massa?"),
    ("5B", "boarding pass",          "cartão de embarque."),
    ("5B", "passport",               "passaporte."),

    # File 6 — Jobs, routines, frequency
    ("6A", "Because",                "Porque..."),
    ("6A", "Great to see you",       "Que bom te ver!"),
    ("6A", "How awful",              "Que horrível!"),
    ("6A", "I love your shoes",      "Adorei seus sapatos."),
    ("6A", "What does she do?",      "O que ela faz (de profissão)?"),
    ("6B", "person",                 "pessoa."),
    ("6B", "every morning",          "toda manhã."),
    ("6B", "feel tired",             "sentir cansado."),
    ("6B", "on the way to work",     "no caminho para o trabalho."),
    ("6B", "What time do you get up?","Que horas você acorda?"),

    # File 7 — Weekend, free time, movies
    ("7A", "definitely",             "definitivamente."),
    ("7A", "depends",                "depende."),
    ("7A", "exciting",               "empolgante."),
    ("7A", "fan",                    "fã."),
    ("7A", "less",                   "menos."),
    ("7B", "don't cry",              "não chore."),
    ("7B", "Don't move",             "Não se mexa."),
    ("7B", "don't say anything",     "não diga nada."),
    ("7B", "I don't remember",       "Eu não lembro."),
    ("7B", "What about",             "E quanto a... / Que tal..."),

    # File 8 — Can / can't, like + ing
    ("8A", "a written test",         "uma prova escrita."),
    ("8A", "I'm free",               "Estou livre / Sou livre."),
    ("8A", "learn to drive",         "aprender a dirigir."),
    ("8A", "start the car",          "ligar o carro."),
    ("8A", "Yes, of course",         "Sim, claro."),
    ("8B", "We love hiking",         "Nós adoramos fazer trilhas."),
    ("8B", "very peaceful",          "muito tranquilo."),
    ("8B", "Let's stay at home",     "Vamos ficar em casa."),
    ("8B", "It's really cold",       "Está muito frio."),
    ("8B", "Do you like traveling?", "Você gosta de viajar?"),

    # File 9 — Present continuous, clothes
    ("9A", "Are you sure?",          "Tem certeza?"),
    ("9A", "box office",             "bilheteria."),
    ("9A", "Have a good day",        "Tenha um bom dia."),
    ("9A", "outside",                "(do lado de) fora."),
    ("9A", "towards",                "em direção a / para."),
    ("9B", "I always cook dinner",   "Eu sempre faço o jantar."),
    ("9B", "She washes the dishes",  "Ela lava a louça."),

    # File 10 — Hotels, was/were
    ("10A", "Enjoy your stay",       "Aproveite a estadia."),
    ("10A", "on the second floor",   "no segundo andar."),
    ("10A", "Do you have a room?",   "Você tem um quarto disponível?"),
    ("10A", "Let's check",           "Deixa eu verificar."),
    ("10A", "There's a room",        "Tem um quarto..."),
    ("10B", "century",               "século."),
    ("10B", "last",                  "último(a) / passado(a)."),
    ("10B", "luxury",                "luxo."),
    ("10B", "secret",                "segredo."),
    ("10B", "strong",                "forte."),
    ("10B", "suspect",               "suspeito."),
    ("10B", "together",              "junto(s)."),
    ("10B", "There was a robbery",   "Houve um assalto."),

    # File 11 — Past simple regular/irregular
    ("11A", "abroad",                "no exterior / fora do país."),
    ("11A", "public transportation", "transporte público."),
    ("11A", "organic",               "orgânico."),
    ("11A", "National Park",         "Parque Nacional."),
    ("11A", "trumpet",               "trompete."),
    ("11A", "play tennis",           "jogar tênis."),
    ("11A", "every weekend",         "todo fim de semana."),

    # File 12 — Review (cards limpos do exercício do Strangers on a train)
    ("12A", "stranger",              "estranho / desconhecido."),
    ("12A", "train",                 "trem."),
    ("12A", "got off",               "desceu (do trem/ônibus)."),
    ("12A", "arrived",               "chegou."),
]
