# Полная схема внутренней перелинковки

Эта схема должна быть реализована как данные и правила, а не руками в каждом тексте.

Физическая вложенность URL не заменяет смысловой путь лечения. `/uslugi/kodirovanie/` больше не находится внутри `/uslugi/lechenie-alkogolizma/`, но эти страницы по-прежнему ссылаются друг на друга там, где это следующий шаг помощи.

## 1. Базовый принцип

У каждой индексируемой страницы есть один основной родитель. Хлебные крошки, URL, меню раздела и XML-карта должны показывать один и тот же путь. Не создавать страницу одновременно в двух SILO.

Каждая коммерческая страница получает ссылки пяти типов: вверх на родителя; на 3–6 соседних страниц своей сущности; на следующий логичный этап помощи; на профильного специалиста; на цену и документы. Ссылки должны быть обычными HTML `<a href>`. Не связывать страницу с десятками других только из-за общей тематики.

## 2. Хабы

`/uslugi/` ведёт на все SILO первого уровня:

- `/uslugi/narkologicheskaya-pomosh/`
- `/uslugi/narkolog-na-dom/`
- `/uslugi/vyvod-iz-zapoya/`
- `/uslugi/kapelnitsy/`
- `/uslugi/kodirovanie/`
- `/uslugi/lechenie-alkogolizma/`
- `/uslugi/snyatie-lomki/`
- `/uslugi/lechenie-narkomanii/`
- `/uslugi/drugie-zavisimosti/`
- `/uslugi/reabilitaciya/`
- `/uslugi/psihiatriya/`
- `/uslugi/psihoterapiya-i-psihologiya/`
- `/uslugi/pomoshch-rodstvennikam/`
- `/uslugi/diagnostika/`
- `/uslugi/vosstanovitelnaya-terapiya/`

Каждый SILO-хаб ведёт на свои дочерние услуги, 1–3 страницы выбора, `/ceny/`, `/vrachi/` и `/o-klinike/licenziya-i-dokumenty/`.

Дочерняя услуга ведёт на родительский хаб и 3–6 смысловых соседей. Не делать глобальный блок на 50 ссылок.

## 3. Нарколог на дом

Родитель URL — `/uslugi/`. Смысловые ссылки: `/uslugi/narkologicheskaya-pomosh/`, `/uslugi/vyvod-iz-zapoya/na-domu/`, `/uslugi/kapelnitsy/ot-zapoya-i-alkogolya/`, `/uslugi/kodirovanie/`, `/uslugi/narkologicheskaya-pomosh/stacionar/`, `/pomoshch/kto-priezzhaet-na-vyzov/`, `/ceny/` и профиль выездной службы.

ГЕО-страницы дополнительно ссылаются по правилам раздела 15. Пример одной локации, только если все четыре URL существуют: нарколог на Белорусской, вывод из запоя на Белорусской, капельница на Белорусской, кодирование на Белорусской.

## 4. Вывод из запоя

`/uslugi/vyvod-iz-zapoya/` ссылается на:

- `/uslugi/vyvod-iz-zapoya/na-domu/`
- `/uslugi/vyvod-iz-zapoya/v-stacionare/`
- `/uslugi/kapelnitsy/`
- `/uslugi/lechenie-alkogolizma/`
- `/uslugi/kodirovanie/`
- `/uslugi/reabilitaciya/`
- `/pomoshch/posle-vyvoda-iz-zapoya/`
- `/pomoshch/dom-ili-stacionar/`
- `/ceny/`

`/uslugi/vyvod-iz-zapoya/na-domu/` при рисках и ограничениях обязательно ссылается на `/uslugi/vyvod-iz-zapoya/v-stacionare/` и `/pomoshch/dom-ili-stacionar/`.

## 5. Капельницы и детокс

`/uslugi/kapelnitsy/` ссылается на `/uslugi/kapelnitsy/ot-zapoya-i-alkogolya/`, `/uslugi/kapelnitsy/ot-pohmelya/`, `/uslugi/kapelnitsy/detoksikaciya/`, `/uslugi/kapelnitsy/alkogolnaya-intoksikaciya/`, `/uslugi/kapelnitsy/abstinentnyj-sindrom/`.

Страницы капельниц ссылаются на `/uslugi/vyvod-iz-zapoya/`, `/uslugi/lechenie-alkogolizma/`, `/pomoshch/posle-vyvoda-iz-zapoya/` и `/ceny/`. Не связывать каждую страницу капельницы со всей ГЕО-матрицей.

## 6. Кодирование

`/uslugi/kodirovanie/` ссылается на форматы, методы, `/uslugi/kodirovanie/preparaty/` и `/uslugi/kodirovanie/raskodirovanie/`.

Любой метод или препарат ссылается на хаб кодирования, 3–5 альтернативных методов, парное раскодирование того же препарата, если такая страница есть, а также на `/uslugi/lechenie-alkogolizma/`, `/uslugi/reabilitaciya/`, `/pomoshch/sryv-posle-kodirovaniya/`, `/ceny/` и профиль врача. Методные и препаратные страницы не получают ГЕО-сетку.

`/uslugi/kodirovanie/raskodirovanie/` ссылается на дочерние страницы раскодирования от Эспераль, Аквилонг, Алгоминал, Дисульфирам, Налтрексон, Вивитрол и Торпедо, на хаб кодирования, `/pomoshch/sryv-posle-kodirovaniya/`, цены и врача.

Каждая страница раскодирования конкретного препарата, например `/uslugi/kodirovanie/raskodirovanie/esperal/`, ссылается на `/uslugi/kodirovanie/raskodirovanie/`, на парную `/uslugi/kodirovanie/preparaty/esperal/`, на 2–3 соседних раскодирования, `/pomoshch/sryv-posle-kodirovaniya/`, `/uslugi/lechenie-alkogolizma/`, цены и врача. Без ГЕО-матрицы и без ссылок на все препараты сразу.

ГЕО есть только у `/uslugi/kodirovanie/`. Такая страница ссылается на общий хаб кодирования и на другие острые услуги этой локации, если их URL есть. Не ссылаться с ГЕО на десятки препаратов и не размножать раскодирование по станциям и городам.

## 7. Лечение алкоголизма

Сегментные и форматные страницы остаются внутри `/uslugi/lechenie-alkogolizma/`: женский, пивной, мужской, хронический, без кодирования, амбулаторно, стационар, на дому. Они ссылаются на общий хаб, на стационар или амбулаторный формат, на `/uslugi/kodirovanie/`, `/uslugi/reabilitaciya/` и профиль врача. Между сегментными страницами максимум 2–4 действительно близких ссылки.

Вывод из запоя, капельницы и кодирование сюда по URL не вложены, но получают смысловые ссылки с хаба лечения алкоголизма.

## 8. Снятие ломки и лечение наркомании

`/uslugi/snyatie-lomki/` ссылается на `/uslugi/snyatie-lomki/na-domu/`, `/uslugi/snyatie-lomki/v-stacionare/`, `/uslugi/lechenie-narkomanii/detoksikaciya/ubod/` если услуга подтверждена, `/uslugi/lechenie-narkomanii/` и `/uslugi/reabilitaciya/narkomaniya/`.

УБОД остаётся дочерней страницей `/uslugi/lechenie-narkomanii/detoksikaciya/` и не становится отдельным SILO.

Каждая страница конкретного вещества ссылается на `/uslugi/lechenie-narkomanii/`, `/uslugi/snyatie-lomki/`, `/uslugi/lechenie-narkomanii/detoksikaciya/`, `/uslugi/lechenie-narkomanii/v-stacionare/`, `/uslugi/reabilitaciya/narkomaniya/`, профиль врача и `/ceny/`. Дополнительно 2–4 соседних вещества, но не полный каталог.

ГЕО лечения наркомании — только города Московской области у хаба `/uslugi/lechenie-narkomanii/moskovskaya-oblast/`. Ссылки: общий хаб, стационар, логистика или трансфер и 4–6 соседних городов этой услуги. Без `вещество × город`.

## 9. Реабилитация

`/uslugi/reabilitaciya/` ссылается на `/uslugi/reabilitaciya/alkogolizm/`, `/uslugi/reabilitaciya/narkomaniya/`, `/uslugi/reabilitaciya/igromaniya/`, `/uslugi/reabilitaciya/12-shagov/` и `/uslugi/reabilitaciya/resocializaciya/`.

Каждая rehab-страница ссылается на соответствующее лечение зависимости, `/uslugi/pomoshch-rodstvennikam/`, `/uslugi/pomoshch-rodstvennikam/sozavisimost/`, профиль специалистов, условия центра или трансфера и `/ceny/`.

ГЕО rehab — только `/uslugi/reabilitaciya/moskovskaya-oblast/` и города под ним, и только при реальном маршруте или трансфере. Ссылки: общий хаб, условия поступления и 4–6 соседних городов. Без метро.

## 10. Психиатрия

`/uslugi/psihiatriya/` ссылается на консультацию, `/uslugi/psihiatriya/psihiatr-na-dom/`, стационар и хабы расстройств.

Хаб расстройства ссылается на дочерние диагнозы, консультацию психиатра, психотерапевта и на стационар или выезд только когда это уместно.

Диагноз ссылается на родительский хаб, 2–4 близких состояния, профильного психиатра и формат лечения. Диагнозы не размножаются по ГЕО.

ГЕО психиатра на дом: округа Москвы и города Московской области. Метро не создавать. Диагноз × город не создавать.

## 11. Помощь родственникам

`/uslugi/pomoshch-rodstvennikam/` ссылается на мотивацию, созависимость, консультацию без пациента и группу.

Эти страницы получают ссылки с `/uslugi/vyvod-iz-zapoya/`, `/uslugi/lechenie-alkogolizma/`, `/uslugi/lechenie-narkomanii/`, `/uslugi/reabilitaciya/`, `/pomoshch/povtornyj-zapoj/` и `/pomoshch/sryv-posle-kodirovaniya/`.

## 12. Trust-страницы

Каждая P0 money-page ссылается на `/ceny/`, `/o-klinike/licenziya-i-dokumenty/`, релевантного специалиста и `/o-klinike/kak-proverit-kliniku/`.

Профиль специалиста ссылается только на услуги, которые он реально оказывает или проверяет. Психолог не выводится автоматически как специалист медицинского выезда.

## 13. Анкоры

Основной анкор — естественное название целевой страницы: «вывод из запоя в стационаре», «лечение пивного алкоголизма», «психиатр на дом». Не делать сквозные exact-match анкоры по 20 раз на странице.

Для ГЕО допустимы «нарколог у метро Белорусская», «вывод из запоя в Химках», «помощь в ВАО». В анкоре можно называть тип территории, но в хлебных крошках и URL нет пунктов «Метро», «Округа» и «Города».

## 14. Ограничения

Не делать:

- `вещество × метро`
- `препарат кодирования × метро`
- `раскодирование × метро`
- `диагноз психиатрии × город`
- страницы улиц
- технические каталоги metro, okrug, mo и goroda в публичном URL
- вложение станции в URL округа
- второй URL того же интента
- одну и ту же станцию в нескольких canonical URL
- индексируемые фильтры с произвольными комбинациями
- перекрёстные блоки на сотни ссылок
- ссылки на несуществующие комбинации услуга × локация

## 15. ГЕО-перелинковка

ГЕО разрешено только у страниц, где это записано в `geo_policy` архитектуры. Хаб региона — родитель локальных страниц.

Хлебные крошки:

```text
Главная
→ Услуги
→ Кодирование
→ Белорусская
```

```text
Главная
→ Услуги
→ Кодирование
→ ВАО
```

```text
Главная
→ Услуги
→ Кодирование
→ Московская область
→ Химки
```

То же правило у вложенной услуги. Для вывода из запоя на дому родитель Москвы — сама страница «на дому»:

```text
Главная
→ Услуги
→ Вывод из запоя
→ На дому
→ Белорусская
```

Соответствующие URL:

- `/uslugi/kodirovanie/`
- `/uslugi/kodirovanie/belorusskaya/`
- `/uslugi/kodirovanie/vao/`
- `/uslugi/kodirovanie/moskovskaya-oblast/`
- `/uslugi/kodirovanie/moskovskaya-oblast/himki/`
- `/uslugi/vyvod-iz-zapoya/na-domu/belorusskaya/`
- `/uslugi/vyvod-iz-zapoya/na-domu/vao/`
- `/uslugi/vyvod-iz-zapoya/na-domu/moskovskaya-oblast/himki/`

Станция и округ — прямые дочерние URL услуги. Связь станции с округом берётся только из `profilactica_geo_relationships.csv`. Не определять округ по строке URL или по названию станции.

### Москва

Страница услуги, для которой разрешены метро и округа, сама является московским родителем. Например `/uslugi/kodirovanie/` ссылается на свои методы и форматы, на все округа Москвы этой услуги и на станции метро этой услуги. Города Московской области идут через `/uslugi/kodirovanie/moskovskaya-oblast/`.

### Округ

Например `/uslugi/kodirovanie/vao/`:

- базовая услуга `/uslugi/kodirovanie/`
- только станции, у которых в `profilactica_geo_relationships.csv` канонический округ `vao`
- 2–4 соседних округа из `profilactica_geo_okrug_neighbors.csv`, и только если такие страницы есть у этой услуги
- связанные услуги в ВАО только если их GEO URL реально существуют

Страница ВАО не показывает Белорусскую, Киевскую, Юго-Западную и другие станции чужих округов. У ЗелАО и ТАО в текущем наборе нет станций: блок метро остаётся пустым, чужие станции не подставляются.

### Метро

Например `/uslugi/kodirovanie/belorusskaya/`:

- базовая услуга `/uslugi/kodirovanie/`
- канонический округ этой станции: для Белорусской это `/uslugi/kodirovanie/cao/`
- 4–6 соседних станций того же канонического округа
- аналогичные услуги у этой станции только если их GEO URL есть

Соседние станции не выбираются по алфавиту и не берутся из общей выборки Москвы. Пока в репозитории нет отдельного графа линий, блок соседних станций не заполняется автоматически: ограничение «только свой округ» уже задано таблицей связей, а конкретные 4–6 соседей нельзя выдумывать из названия.

Одна станция имеет один canonical-округ и один URL на услугу, даже если вестибюли выходят в разные территории. Неоднозначность записана в `notes` таблицы связей.

### Московская область

`/moskovskaya-oblast/` ссылается на базовую услугу и на города, отобранные для этой услуги. Станции метро и округа Москвы на этот хаб не выводятся.

Страница города ссылается на хаб области, базовую услугу, 4–6 соседних городов этой же услуги и на страницы других услуг в этом городе только если они есть. Соседние города не выбираются по алфавиту. Не создавать ссылку, если городского URL другой услуги нет.

У лечения алкоголизма на дому, лечения наркомании и реабилитации есть только областной хаб: метро и округа для этих услуг не предусмотрены.
