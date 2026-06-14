===============================================================================
  AEF Self-Study  —  American English File (3e) navegável e com tracking
===============================================================================

O QUE É
-------
Site local que indexa todo o material da coleção American English File 3e
presente nesta pasta (Starter → Advanced) e oferece:

  • Navegação por curso → unidade → recurso (SB / WB / PE / Listening /
    Review & Check / Episodes / Practice / Tests / Teacher's Guide / Extras)
  • Visualização de PDFs no viewer nativo do browser, com salto por página
  • Player inline de áudio e vídeo, com posição retomada automaticamente
  • Marcação de concluído ✓, favorito ⭐ e notas livres por recurso
  • Dashboard com streak diário, minutos de listening, progresso por curso
  • Exportar progresso em JSON para backup
  • Banco SQLite local (data/study.db) — backup = copiar 1 arquivo

100% offline. Nenhum material externo é usado — só o conteúdo desta pasta.


REQUISITOS
----------
  • Python 3.10 ou superior  (testado com Python 3.14 no macOS)
  • Um navegador moderno (Chrome, Safari, Firefox, Edge)
  • ~50 MB livres para o ambiente virtual e o banco
  • O material AEF nas pastas:
        "AEF 0 starter"
        "AEF 1 elementary"
        "AEF 2 pre-intermediate"
        "AEF 3 intermediate"
        "AEF 4 upper-intermediate"
        "AEF 5 advanced"


COMO RODAR
----------
Abra o Terminal nesta pasta e execute:

    ./start.sh

Na primeira execução, o script:
  1) cria um ambiente virtual em .venv/
  2) instala as dependências (FastAPI, Uvicorn, SQLAlchemy)
  3) roda o indexador (gera data/index.json)
  4) sobe o servidor em http://127.0.0.1:8000

Depois é só abrir esse endereço no navegador.

Para parar: Ctrl+C no terminal.
Para subir de novo, basta rodar ./start.sh — daí em diante é instantâneo.


ESTRUTURA DESTA PASTA
---------------------
  AEF 0 starter/                  Material original (não é alterado)
  AEF 1 elementary/               idem
  …
  AEF 5 advanced/                 idem

  app/                            Código da aplicação
    main.py                       backend FastAPI: páginas + API + /files
    db.py                         modelos SQLAlchemy (progresso, notas, sessões)
    static/                       front-end (HTML/CSS/JS puro, sem build)
      index.html                  Home (grid dos cursos)
      course.html                 Curso (abas + sidebar de unidades)
      dashboard.html              Dashboard de progresso
      css/                        theme.css (cores) + app.css (layout)
      js/
        api.js                    wrapper de fetch para a API
        store.js                  cache em memória + agrupamentos
        components/resource.js    linha de recurso (audio/video/pdf/doc/test)
        pages/                    home.js, course.js, dashboard.js

  scripts/
    build_index.py                varre as pastas e gera data/index.json

  data/
    index.json                    catálogo (gerado pelo script — não editar)
    study.db                      seu progresso (SQLite — único arquivo)

  .venv/                          ambiente virtual Python (gerado pelo start.sh)
  requirements.txt                dependências Python
  start.sh                        script para subir tudo
  README.txt                      este arquivo


URLs DA APLICAÇÃO
-----------------
  http://127.0.0.1:8000/          Home (lista os 6 cursos)
  http://127.0.0.1:8000/course?id=elementary&tab=SB&unit=3
                                  Página de curso (id ∈ starter, elementary,
                                  pre-intermediate, intermediate,
                                  upper-intermediate, advanced)
  http://127.0.0.1:8000/dashboard Dashboard com estatísticas

API (interna, usada pelo front-end)
  GET  /api/index                 catálogo completo
  GET  /api/stats                 estatísticas para o dashboard
  GET  /api/progress              progresso e notas
  POST /api/progress              marca concluído / favorito
  POST /api/position              salva posição da mídia (autosave)
  POST /api/note                  salva nota livre
  GET  /api/export                JSON de backup do banco
  GET  /files/{caminho}           serve PDF / MP3 / MP4 / DOCX


COMO O INDEXADOR ENTENDE O MATERIAL
-----------------------------------
O script scripts/build_index.py lê apenas nomes de arquivos (jamais altera
o conteúdo das pastas) e reconhece padrões como:

  AEF3e_Level_2_SB_3.05.mp3       → SB Audio, Unit 3, faixa 3.05
  AEF3e_Level_1_WB_7.2.mp3        → WB Audio, Unit 7, faixa 7.2
  AEF3e_SB1_PE_Ep4_*.mp4          → Practical English, Episode 4
  AEF3e_SB2_Review_and_Check_5&6  → Review & Check, cobre Units 5 e 6
  3B Love me, love my dog.docx    → Practice, Unit 3 Lição B
  AEF3e_L1_filetest_05a.pdf       → Tests · File Test, Unit 5
  Unit 1/  Unit 2/  …             → fallback: unidade pelo nome da pasta

Variações tratadas:
  • Starter: SB Audio fica dentro de EndofСourseTest/Unit N/.
  • Levels 4 e 5: SB Audio (e WB Audio no L5) divididos por Unit N/.
  • Levels 1-3: SB e WB Audio em pastas …_All_Audio/ com unidade no nome.
  • Teacher's Guide pode se chamar TG.pdf (L0-L3) ou TB.pdf (L4-L5).

Reexecute o indexador a qualquer momento se adicionar/mover arquivos:

    ./.venv/bin/python scripts/build_index.py


PROGRESSO E BACKUP
------------------
Todo o seu progresso vive em DOIS arquivos:

  data/study.db        ← banco SQLite (autoridade)
  data/index.json      ← regenerável a partir das pastas

Backup recomendado:
  1) Pelo dashboard: clique em "Exportar progresso (JSON)".
  2) Ou copie data/study.db para outro lugar (pendrive, nuvem, etc).

Para começar do zero: apague data/study.db e rode ./start.sh novamente.


SOLUÇÃO DE PROBLEMAS
--------------------
"./start.sh: command not found"
    Garanta que está na pasta certa: cd "/Users/tialmachado/Documents/English Course"
    Garanta que tem permissão de execução: chmod +x start.sh

"address already in use"
    Outro processo está usando a porta 8000. Pare-o ou edite start.sh
    e troque a porta (ex.: --port 8765).

PDF / áudio / vídeo não abre
    Verifique se o arquivo ainda existe na pasta original e se nomes
    de pasta não foram renomeados. Reexecute o indexador.

Quero adicionar um arquivo novo
    Coloque na pasta correta seguindo a convenção de nomes acima e
    rode novamente: ./.venv/bin/python scripts/build_index.py


PRINCIPAIS DECISÕES DE DESIGN
-----------------------------
  • HTML/CSS/JS puro no front (sem React/Vue/Svelte). Zero build.
  • PDF aberto no viewer nativo do browser (sem extração de conteúdo).
  • Backend FastAPI + SQLite só para persistir progresso.
  • Material original nunca é modificado, renomeado ou copiado.
  • Single-user, local, offline.


PRÓXIMAS IMPLEMENTAÇÕES
-----------------------
Lista de evoluções planejadas, ordenadas por impacto no preparo para
certificações (Cambridge / TOEFL / IELTS).

TIER 1 — Maior impacto na retenção e nas habilidades
....................................................

  [ ] Flashcards SRS (Anki-style) para vocabulário
      Vocab extraído do TG vira deck por curso. Algoritmo Leitner (3
      caixas) ou SM-2: revê 10–15 cartões por dia, sistema espaça
      baseado em acertos. Maior multiplicador de retenção que existe
      pra estudo de língua.

  [ ] Loop A-B + velocidade fina (0.5×–2×) no player
      Seleciona dois pontos do áudio (click=A, click=B) e ele toca em
      loop aquela frase. Essencial para shadowing (repetir junto pra
      pronúncia).

  [ ] Modo ditado
      Toca o áudio do SB, você digita o que ouve, compara com o
      script (já existe em Video/Practice/Audio Script/ ou no TG).
      Treina listening + spelling + gramática junto.

  [ ] Gravação da própria voz
      Grava você lendo/falando (browser MediaRecorder), salva, você
      compara depois com o áudio original. Self-grading + favoritar
      pra revisitar.

TIER 2 — Qualidade de vida que move a agulha
............................................

  [ ] Transcript sincronizado com áudio
      Para SB Audio e PE: mostra o script (extraído dos PDFs) e
      destaca a linha conforme toca. Click numa linha pula o áudio
      pra ali. Pra shadowing fica imbatível.

  [ ] Busca de palavra/frase pela coleção
      Digita "anyway", vê todas as ocorrências em SB/WB/TG dos 6
      cursos com contexto. Útil pra entender uso real e collocations.

  [ ] Modo simulação de prova
      Cronômetro + bloqueia favoritos/notas durante a "prova", pega
      listening e reading dos próprios SB. Útil semanas antes do
      Cambridge / TOEFL.

TIER 3 — Bom mas opcional
.........................

  [ ] Sound Bank ligado por símbolo fonético
      Clica num /ʃ/ num tópico de aula, toca o áudio do Sound Bank
      do SB.

  [ ] Daily review
      Ao fazer check-in, o sistema sugere "revise 3 momentos da
      semana passada" (pega steps marcados há 7 dias).

  [ ] Reading speed tracker em textos do SB
      Cronometra, calcula WPM, mostra evolução.

  [ ] Export Anki (.apkg)
      Se você já usa Anki em paralelo.

  [ ] Phrasal verbs / idioms drill específico
      TG marca eles em quase toda aula — vira uma lista filtrável.

  [ ] Empacotamento PyInstaller para rodar de pendrive
      Sem instalar Python (binários Mac/Windows, abre servidor +
      browser ao clicar).

  [ ] Importar JSON de progresso (já existe o exportar)

  [ ] "Próximo recomendado" no dashboard


CONTEÚDO INDEXADO
-----------------
  Starter (A1)             460 recursos / 12 units
  Elementary (A1/A2)       707 recursos / 12 units
  Pre-Intermediate (A2/B1) 679 recursos / 12 units
  Intermediate (B1)        600 recursos / 10 units
  Upper-Intermediate (B2)  316 recursos / 10 units
  Advanced (C1)            227 recursos / 10 units
  Total: 2989 recursos.

Bons estudos!
