from __future__ import annotations

import re


def _normalize_name(value: str) -> str:
    return " ".join(value.strip().upper().split())


CATEGORY_TRANSLATIONS = {
    "BLACK COFFEE": "Black Coffee",
    "COFFEE&MILK": "Coffee & Milk",
    "LATTE": "Latte",
    "RAF COFFEE": "Raf",
    "ICED COFFEE": "Iced Coffee",
    "NOT COFFEE": "Not Coffee",
    "TEA": "Tea",
    "COLD DRINKS": "Cold Drinks",
    "COCKTAILS": "Cocktails",
    "SYRUPS/SAUCES": "Syrups & Sauces",
}

DRINK_NAME_DISPLAY = {
    "DOUBLE ESPRESSO": "Double Espresso",
    "AMERICANO": "Americano",
    "HARIO V60": "Hario V60",
    "CHEMEX": "Chemex",
    "BLACK STRAWBERRY": "Black Strawberry",
    "FRENCHPRESS": "French Press",
    "HOOP": "Hoop",
    "CORTADO": "Cortado",
    "CAPPUCCINO": "Cappuccino",
    "FLAT WHITE": "Flat White",
    "LATTE": "Latte",
    "LATTE SINGAPORE": "Latte Singapore",
    "LATTE SALTED CARAMEL": "Latte Salted Caramel",
    "LATTE SAHARA": "Latte Sahara",
    "LATTE HALVA": "Latte Halva",
    "LATTE SPANISH": "Latte Spanish",
    "LATTE CANADA": "Latte Canada",
    "VANILLA": "Vanilla",
    "ORANGE": "Orange",
    "LAVENDER": "Lavender",
    "RAF HALVA": "Raf Halva",
    "MIMOZA": "Mimoza",
    "POP CORN": "Pop Corn",
    "ESPRESSO TONIC": "Espresso Tonic",
    "COLD BREW TONIC": "Cold Brew Tonic",
    "COLD BREW": "Cold Brew",
    "BUMBLE": "Bumble",
    "CHERRY CREAM": "Cherry Cream",
    "BOUNTY": "Bounty",
    "ICE LATTE": "Ice Latte",
    "ICE CAPPUCCINO": "Ice Cappuccino",
    "ICE AMERICANO": "Ice Americano",
    "ICE SINGAPORE": "Ice Singapore",
    "ICE CARAMEL": "Ice Caramel",
    "ICE CANADA": "Ice Canada",
    "ICE SPANISH": "Ice Spanish",
    "CHERRY ICE MATCHA": "Cherry Ice Matcha",
    "ICECACAO": "Ice Cacao",
    "ICE MATCHA": "Ice Matcha",
    "CACAO": "Cacao",
    "VANILLA SKY": "Vanilla Sky",
    "LATTE CHICORY": "Latte Chicory",
    "LATTE MATCHA": "Latte Matcha",
    "ASSAM TEA": "Assam Tea (Black Tea)",
    "DARJEELING TEA": "Darjeeling Tea",
    "GREEN TEA": "Green Tea",
    "JASMINE TEA": "Jasmine Tea",
    "EASY BREATHING": "Easy Breathing",
    "WILD BERRY": "Wild Berry",
    "TIEGUANYIN": "Tieguanyin",
    "SEA BUCKTHORN": "Sea Buckthorn",
    "BLACK CURRANT": "Black Currant",
    "MILKY OOLONG": "Milky Oolong",
    "ICE SIBERIAN": "Ice Siberian",
    "ICE BLACKCURRANT": "Ice Blackcurrant",
    "ICE SIBERIAN(BOTTLE)": "Ice Siberian (Bottle)",
    "ICE BLACKCURRANT(BOTTLE)": "Ice Blackcurrant (Bottle)",
    "SMOOTHIE": "Smoothie",
    "LEMONADE": "Lemonade",
    "CHERRY LEMONADE": "Cherry Lemonade",
    "GLUHWEIN N/A": "Gluhwein N/A",
    "APEROL SPRITZ": "Aperol Spritz",
    "RUBY SUNSET": "Ruby Sunset",
    "SALTED CARAMEL": "Salted Caramel",
    "VANILLA SUGAR": "Vanilla Sugar",
    "SINGAPORE": "Singapore",
    "ORANGE POWDER": "Orange Powder",
    "LAVANDER POWDER": "Lavander Powder",
    "MIX CREAM(RAF)": "Mix Cream (Raf)",
    "SIMPLE SYRUP(SUGAR)": "Simple Syrup (Sugar)",
    "SEA BUCKTHORN SAUCE": "Sea Buckthorn Sauce",
    "BLACK CURRANT SAUCE": "Black Currant Sauce",
    "HALVA SUACE": "Halva Sauce",
    "CARAMEL SYRUP(BUMBLE)": "Caramel Syrup (Bumble)",
    "CACAO SAUCE": "Cacao Sauce",
}

INGREDIENT_TRANSLATIONS = {
    "milk": "молоко",
    "steamed milk": "взбитое молоко",
    "hot water": "горячая вода",
    "filtered water": "фильтрованная вода",
    "filtred water": "фильтрованная вода",
    "ice cubes": "кубики льда",
    "ice cube": "кубик льда",
    "tonic": "тоник",
    "sparkling water": "газированная вода",
    "sparkling wine": "игристое вино",
    "orange juice": "апельсиновый сок",
    "lime juice": "сок лайма",
    "lemon juice": "лимонный сок",
    "coconut milk": "кокосовое молоко",
    "oat milk": "овсяное молоко",
    "oat  milk": "овсяное молоко",
    "mix cream": "смесь сливок",
    "fat cream (>30%)": "жирные сливки (>30%)",
    "fat cream": "жирные сливки",
    "fat cream >30%": "жирные сливки >30%",
    "cold brew concentrate": "концентрат колд брю",
    "cold brew concetrate": "концентрат колд брю",
    "cold filter": "холодный фильтр",
    "singapore sauce": "соус Singapore",
    "salted caramel": "соленая карамель",
    "halva saucе": "халвенный соус",
    "halva sauce": "халвенный соус",
    "condensed milk": "сгущенное молоко",
    "orange powder": "апельсиновая пудра",
    "lavander powder": "лавандовая пудра",
    "vanilla sugar": "ванильный сахар",
    "maple syrup": "кленовый сироп",
    "dates syrup": "финиковый сироп",
    "coconut syrup": "кокосовый сироп",
    "caramel syrup": "карамельный сироп",
    "cherry syrup": "вишневый сироп",
    "black currant sauce": "соус из черной смородины",
    "blackcurrant": "черная смородина",
    "water": "вода",
    "seabuckthorn": "облепиха",
    "seabuckthorn sauce": "облепиховый соус",
    "sea buckthorn sauce": "облепиховый соус",
    "rosemary": "розмарин",
    "tabasco": "табаско",
    "carnation": "гвоздика",
    "matcha": "матча",
    "chicory": "цикорий",
    "lemongrass": "лемонграсс",
    "dried orange zest": "сушеная апельсиновая цедра",
    "dried lemon zest": "сушеная лимонная цедра",
    "dried lavender": "сушеная лаванда",
    "dried lavander": "сушеная лаванда",
    "frozen strawberry": "замороженная клубника",
    "banana": "банан",
    "schweppes": "Schweppes",
    "ginger": "имбирь",
    "salt": "соль",
    "milk (barista)": "молоко бариста",
    "cherry bitter": "вишневый биттер",
    "sea buckthorn berries": "ягоды облепихи",
    "cacao powder/50gr cacao sauce": "какао-порошок / 50 г какао-соуса",
    "cacao powder": "какао-порошок",
    "cacao sauce": "какао-соус",
    "white sugar": "белый сахар",
    "sugar": "сахар",
}

TEXT_REPLACEMENTS = [
    ("fill up cacaos' cup with 40gr hot water", "налейте 40 г горячей воды в чашку для какао"),
    ("fill up cacaos' cup with 40 g hot water", "налейте 40 г горячей воды в чашку для какао"),
    ("fill up cacaos' cup with 40gr горячая вода", "налейте 40 г горячей воды в чашку для какао"),
    ("fill up cacaos' cup with 40 g горячая вода", "налейте 40 г горячей воды в чашку для какао"),
    ("pour into the pitcher milk and sugar", "налейте молоко и добавьте сахар в питчер"),
    ("pour in the pitcher milk and sugar", "налейте молоко и добавьте сахар в питчер"),
    ("steamed it", "взбейте паром"),
    ("steamed it and serve", "взбейте паром и подавайте"),
    ("add all to the saucepan", "добавьте все ингредиенты в сотейник"),
    ("leave the saucepan for 10 minutes at medium power-temperature", "оставьте сотейник на среднем нагреве на 10 минут"),
    ("leave the saucepan for 10 minutes at medium power - temperature", "оставьте сотейник на среднем нагреве на 10 минут"),
    ("leave the saucepan for 10 minutes at low power-temperature", "оставьте сотейник на слабом нагреве на 10 минут"),
    ("leave the saucepan for 10 minutes at low power - temperature", "оставьте сотейник на слабом нагреве на 10 минут"),
    ("place the liquid and berries in a blender and blend until smooth", "перелейте жидкость с ягодами в блендер и пробейте до однородности"),
    ("place the liquid и berries in a blender и blend until smooth", "перелейте жидкость с ягодами в блендер и пробейте до однородности"),
    ("strain and pour into a container", "процедите и перелейте в контейнер"),
    ("strain и влейте into a container", "процедите и перелейте в контейнер"),
    ("prepare espresso using brew ratio", "приготовьте эспрессо с brew ratio"),
    ("the weight of the espresso must be within", "вес эспрессо должен быть в пределах"),
    ("mix hot and cold water into the  cup", "смешайте горячую и холодную воду в чашке"),
    ("mix hot and cold water into the cup", "смешайте горячую и холодную воду в чашке"),
    ("pour double espresso into the water", "влейте двойной эспрессо в воду"),
    ("put 18 grams of grounded beans into a moistened filter", "поместите 18 граммов молотого зерна в смоченный фильтр"),
    ("put 90gr of the frozen strawberry into the server", "поместите 90 г замороженной клубники в сервер"),
    ("put the rosemary in tea pot", "положите розмарин в чайник"),
    ("add blackcurrant suace", "добавьте соус из черной смородины"),
    ("put 18 grams of grounded beans into a moistened filter", "поместите 18 граммов молотого зерна в смоченный фильтр"),
    ("add water according to the recipe", "добавьте воду по рецепту"),
    ("amount of pours", "количество проливов"),
    ("slowly pour 400gr of water from the center in a spiral", "медленно влейте 400 г воды от центра по спирали"),
    ("pour in the entire volume of water(on the sides)", "влейте весь объем воды по стенкам"),
    ("wait for 30sec", "подождите 30 секунд"),
    ("wait for 30 sec", "подождите 30 секунд"),
    ("pour in the remaining milk", "влейте оставшееся молоко"),
    ("the remaining milk", "оставшееся молоко"),
    ("the espresso into the milk", "эспрессо в молоко"),
    ("pour in the espresso into the milk", "влейте эспрессо в молоко"),
    ("pour in the espresso into the cup", "влейте эспрессо в чашку"),
    ("serve with sesame seeds and halva on top", "подавайте с кунжутом и халвой сверху"),
    ("serve with pop corn on top", "подавайте с попкорном сверху"),
    ("with sesame seeds and halva on top", "с кунжутом и халвой сверху"),
    ("and create art with etching technique", "и сделайте рисунок в технике etching"),
    ("pour a drop of milk", "влейте немного молока"),
    ("stir until the color becomes uniform", "размешайте до однородного цвета"),
    ("then pour in the milk using the latte art technique", "затем влейте молоко в технике латте-арт"),
    ("prepare a single espresso into the cup", "приготовьте одинарный эспрессо в чашку"),
    ("prepare a single/double espresso into the cup", "приготовьте одинарный/двойной эспрессо в чашку"),
    ("prepare a double espresso into the cup", "приготовьте двойной эспрессо в чашку"),
    ("prepare a double espresso into the small pitcher", "приготовьте двойной эспрессо в маленький питчер"),
    ("prepare a double espresso into the small pitcher", "приготовьте двойной эспрессо в маленький питчер"),
    ("prepare a double espresso into the pitcher", "приготовьте двойной эспрессо в питчер"),
    ("prepare an espresso into the pitcher", "приготовьте эспрессо в питчер"),
    ("prepare an espresso into the small pitcher", "приготовьте эспрессо в маленький питчер"),
    ("prepare a double espresso into the small pitcher", "приготовьте двойной эспрессо в маленький питчер"),
    ("prepare an espresso into the pitcher", "приготовьте эспрессо в питчер"),
    ("prepare an espresso into the small pitcher", "приготовьте эспрессо в маленький питчер"),
    ("add ice into the glass", "добавьте лед в стакан"),
    ("add tonic", "добавьте тоник"),
    ("add tonic and cold brew on top", "добавьте тоник и сверху влейте колд брю"),
    ("pour in an espresso on top", "влейте сверху эспрессо"),
    ("pour in the cream", "влейте сливки"),
    ("pour in the liquid", "влейте жидкость"),
    ("add syrup to the cup", "добавьте сироп в чашку"),
    ("add syrup to the pitcher with milk, steam it and pour in the glass", "добавьте сироп в питчер с молоком, взбейте и перелейте в стакан"),
    ("add all ingredients in pitcher", "добавьте все ингредиенты в питчер"),
    ("steam the milk", "взбейте молоко паром"),
    ("steamed it and serve", "взбейте паром и подавайте"),
    ("add all ingredients to blender and blend at maximum power for 30 seconds", "добавьте все ингредиенты в блендер и взбейте на максимальной мощности в течение 30 секунд"),
    ("mix it thoroughly", "тщательно перемешайте"),
    ("mix twice and garnish", "перемешайте дважды и украсьте"),
    ("classic indian black tea", "классический индийский черный чай"),
    ("tea grown in the vicinity of the city of the same name in the northern mountainous part of india in the himalayas, collected and manufactured under certain conditions. plantations are located at an altitude of 750-2000 meters above sea level", "чай, выращенный в окрестностях одноименного города в северной горной части Индии, в Гималаях. Собирается и производится при особых условиях. Плантации расположены на высоте 750-2000 метров над уровнем моря"),
    ("the finished drink has a characteristic floral aroma. the taste combines sweetish shades and sourness. the aftertaste is velvety, honey.", "готовый напиток обладает характерным цветочным ароматом. Во вкусе сочетаются сладковатые оттенки и кислинка. Послевкусие бархатистое, медовое."),
    ("light breath herbal tea is ideal for a relaxing break. the tea consists of a unique blend of linden flowers, fenugreek seeds, mint leaves, sage and thyme. all these ingredients have a long tradition in folk medicine and are known for their positive properties.", "травяной чай «Легкое дыхание» идеально подходит для расслабляющей паузы. В составе уникальная смесь цветов липы, семян пажитника, листьев мяты, шалфея и тимьяна. Все эти ингредиенты давно используются в народной медицине и известны своими полезными свойствами."),
    ("ingredients: apple pieces, hibiscus, birch leaves, elderberry, blackberry leaves, verbena leaves, strawberry, blackberry, raspberry and blueberry", "состав: кусочки яблока, гибискус, листья березы, бузина, листья ежевики, листья вербены, клубника, ежевика, малина и черника"),
    ("grind the filter coffee beans at grinding level 15", "измельчите зерно для фильтра на уровне помола 15"),
    ("200 grams of ground filter coffee beans fill with 1l of water.", "200 г молотого зерна для фильтра залейте 1 л воды."),
    ("leave for 16 hours", "оставьте на 16 часов"),
    ("1 part cold brew, two parts filtered water", "1 часть колд брю и 2 части фильтрованной воды"),
    ("73 grams of cold brew preparation + 146 grams of filtred water", "73 г заготовки колд брю + 146 г фильтрованной воды"),
    ("single/double - espresso", "одинарный/двойной эспрессо"),
    ("single/double espresso", "одинарный/двойной эспрессо"),
    ("single/double - espresso", "одинарный/двойной эспрессо"),
    ("single espresso", "одинарный эспрессо"),
    ("double espresso", "двойной эспрессо"),
    ("steamed milk", "взбитое молоко"),
    ("cold brew concentrate", "концентрат колд брю"),
    ("cold brew concetrate", "концентрат колд брю"),
    ("cold filter", "холодный фильтр"),
    ("filter coffee beans", "зерно для фильтра"),
    ("coffee beans", "кофейные зерна"),
    ("filtred water", "фильтрованная вода"),
    ("filtered water", "фильтрованная вода"),
    ("sparkling water", "газированная вода"),
    ("sparkling wine", "игристое вино"),
    ("blackcurrant", "черная смородина"),
    ("seabuckthorn", "облепиха"),
    ("water", "вода"),
    ("tabasco", "табаско"),
    ("carnation", "гвоздика"),
    ("cacao powder/50gr cacao sauce", "какао-порошок / 50 г какао-соуса"),
    ("cacao powder", "какао-порошок"),
    ("cacao sauce", "какао-соус"),
    ("white sugar", "белый сахар"),
    ("sugar", "сахар"),
    ("mix cream", "смесь сливок"),
    ("fat cream", "жирные сливки"),
    ("oat  milk", "овсяное молоко"),
    ("oat milk", "овсяное молоко"),
    ("coconut milk", "кокосовое молоко"),
    ("condensed milk", "сгущенное молоко"),
    ("vanilla sugar", "ванильный сахар"),
    ("orange powder", "апельсиновая пудра"),
    ("lavander powder", "лавандовая пудра"),
    ("lemongrass syrup", "сироп лемонграсс"),
    ("maple syrup", "кленовый сироп"),
    ("dates syrup", "сироп из фиников"),
    ("cherry syrup", "вишневый сироп"),
    ("caramel syrup", "карамельный сироп"),
    ("coconut syrup", "кокосовый сироп"),
    ("lime juice", "сок лайма"),
    ("lemon juice", "лимонный сок"),
    ("orange juice", "апельсиновый сок"),
    ("hot water", "горячая вода"),
    ("ice cubes", "кубики льда"),
    ("ice cube", "кубик льда"),
    ("ice into the glass", "лед в стакан"),
    ("slice of lime/lemon", "долька лайма/лимона"),
    ("slice of an orange", "долька апельсина"),
    ("slice of a lemon", "долька лимона"),
    ("slice of lime", "долька лайма"),
    ("slice of lemon", "долька лимона"),
    ("create art with etching technique", "сделайте рисунок в технике etching"),
    ("whip it with an electric whisk within 15 seconds", "взбейте электрическим венчиком в течение 15 секунд"),
    ("whip the cream with an electric whisk within 30 seconds", "взбейте сливки электрическим венчиком в течение 30 секунд"),
    ("add all ingredients to a glass, mix thoroughly and garnish with lemon slice", "добавьте все ингредиенты в стакан, тщательно перемешайте и украсьте долькой лимона"),
    ("add all ingredients to a glass, mix thoroughly", "добавьте все ингредиенты в стакан и тщательно перемешайте"),
    ("add all ingredients to the kettle and stir with a spoon.", "добавьте все ингредиенты в чайник и перемешайте ложкой."),
    ("recommended", "рекомендуем"),
    ("brewing for 3 minutes", "заваривать 3 минуты"),
    ("brewing for 5 minutes", "заваривать 5 минут"),
    ("boil a kettle at 95 degrees with filtered water", "вскипятите чайник с фильтрованной водой до 95 градусов"),
    ("boil a kettle at 85 degrees with filtered water", "вскипятите чайник с фильтрованной водой до 85 градусов"),
    ("boil a kettle at 100 degrees with filtered water", "вскипятите чайник с фильтрованной водой до 100 градусов"),
    ("add tea to the tea pot", "добавьте чай в чайник"),
    ("add water to the tea pot", "добавьте воду в чайник"),
    ("add hot water to the tea pot", "добавьте горячую воду в чайник"),
    ("stir it thoroughly and serve", "тщательно перемешайте и подавайте"),
    ("mix together", "смешайте"),
    ("fill small lattes' cup with 20gr hot water", "налейте 20 г горячей воды в маленькую чашку для латте"),
    ("fill small latte cup with 20gr hot water", "налейте 20 г горячей воды в маленькую чашку для латте"),
    ("add powder and syrup into the glass", "добавьте порошок и сироп в стакан"),
    ("stir it with spoon thoroughly", "тщательно перемешайте ложкой"),
    ("steamed milk and pour in the milk using the latte art technique.", "взбейте молоко паром и влейте его в стакан в технике латте-арт."),
    ("cut the dry part of the lemongrass, and then push the entire stem with a muddler.", "срежьте сухую часть лемонграсса, затем раздавите стебель мадлером."),
    ("cut the crushed lemongrass into pieces ~ 3-4 cm each.", "нарежьте раздавленный лемонграсс на кусочки по 3-4 см."),
    ("add white sugar to a saucepan and melt until it becomes a liquid caramel. (important: do not bring the caramel to a state and do not let it “burn”)", "добавьте белый сахар в сотейник и растопите до состояния жидкой карамели. Важно: не дайте карамели подгореть."),
    ("add lemongrass to the saucepan with caramel and mix thoroughly, gradually reducing power and temperature.", "добавьте лемонграсс в сотейник с карамелью и тщательно перемешайте, постепенно уменьшая нагрев."),
    ("add cream mix. stir and leave on low power-temperature for 10 minutes.", "добавьте смесь сливок, перемешайте и оставьте на слабом нагреве на 10 минут."),
    ("add white sugar to a saucepan and melt until it reaches a liquid caramel color. (important: do not let the caramel turn black and do not let it “burn”)", "добавьте белый сахар в сотейник и растопите до жидкой карамели. Важно: не дайте карамели почернеть и подгореть."),
    ("add the cream mix to the saucepan. stir and leave on low power-temperature for 10 minutes.", "добавьте смесь сливок в сотейник, перемешайте и оставьте на слабом нагреве на 10 минут."),
    ("carefully add water to the saucepan.", "аккуратно добавьте воду в сотейник."),
    ("place all ingredients in a blender, blend until smooth (there should be no lumps)", "поместите все ингредиенты в блендер и взбейте до однородности, без комочков."),
    ("beat everything at high power until smooth, shaking the glasses periodically for a better result.", "измельчите все на высокой скорости до однородности, периодически встряхивая стакан блендера."),
    ("mix cream and milk in a bottle.", "смешайте смесь сливок и молоко в бутылке."),
    ("at medium power-temperature, periodically stirring until the sugar is completely dissolved", "держите на среднем нагреве, периодически помешивая, пока сахар полностью не растворится."),
    ("add all the ingredients to the kettle and stir with a spoon.", "добавьте все ингредиенты в чайник и перемешайте ложкой."),
    ("add all the ingredients to the pan. cut the fruit into small pieces", "добавьте все ингредиенты в кастрюлю. Нарежьте фрукты небольшими кусочками."),
    ("turn on the medium heat and bring the workpiece to 90-95 degrees", "поставьте на средний огонь и доведите заготовку до 90-95 градусов."),
    ("when serving to the guest, preheat with a steamer to 60 degrees.", "при подаче подогрейте паром до 60 градусов."),
    ("add dried orange and lemon zest and white sugar to the blender.", "добавьте сушеную апельсиновую и лимонную цедру, а также белый сахар в блендер."),
    ("add dried lavender, white sugar and salt to a blender.", "добавьте сушеную лаванду, белый сахар и соль в блендер."),
    ("stir at medium temperature until cocoa is completely dissolved.", "перемешивайте на среднем нагреве, пока какао полностью не растворится."),
    ("create art with etching technique", "сделайте рисунок в технике этчинг"),
    ("garnish with orange slice", "украсьте долькой апельсина"),
    ("garnish with lemon/lime", "украсьте лимоном или лаймом"),
    ("garnish", "украсьте"),
    ("add syrup to the cup", "добавьте сироп в чашку"),
    ("foam 1cm", "пена 1 см"),
    ("foam 1,5cm", "пена 1,5 см"),
    ("foam 0,4mm", "пена 0,4 мм"),
    ("put into pan/pot", "поместить в кастрюлю"),
]


def translate_category_name(value: str) -> str:
    return CATEGORY_TRANSLATIONS.get(_normalize_name(value), value.strip())


def display_drink_name(value: str) -> str:
    normalized = _normalize_name(value)
    if normalized in DRINK_NAME_DISPLAY:
        return DRINK_NAME_DISPLAY[normalized]

    compact = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value.strip())
    if compact:
        return compact
    return value.strip()


def _translate_ingredient_label(value: str) -> str:
    normalized = " ".join(value.strip().split()).lower()
    return INGREDIENT_TRANSLATIONS.get(normalized, value.strip())


def _inflected_ingredient(amount: str, label: str) -> str | None:
    forms = {
        "молоко": "молока",
        "зерно для фильтра": "зерна для фильтра",
        "кофейные зерна": "кофейных зерен",
        "взбитое молоко": "взбитого молока",
        "горячая вода": "горячей воды",
        "фильтрованная вода": "фильтрованной воды",
        "кубики льда": "кубиков льда",
        "апельсиновый сок": "апельсинового сока",
        "сок лайма": "сока лайма",
        "лимонный сок": "лимонного сока",
        "кокосовое молоко": "кокосового молока",
        "овсяное молоко": "овсяного молока",
        "сгущенное молоко": "сгущенного молока",
        "жирные сливки": "жирных сливок",
        "какао-порошок": "какао-порошка",
        "какао-соус": "какао-соуса",
        "белый сахар": "белого сахара",
        "сахар": "сахара",
        "черная смородина": "черной смородины",
        "вода": "воды",
        "облепиха": "облепихи",
        "гвоздика": "гвоздики",
        "замороженная клубника": "замороженной клубники",
        "банан": "банана",
    }
    if label in forms:
        return f"{amount} {forms[label]}"
    return None


def _normalize_line(line: str) -> str:
    value = line.strip()
    if not value:
        return ""

    labelled_patterns = [
        (r"^(?P<amount>.+?)\s*-\s*temperature$", "Температура: {amount}"),
        (r"^(?P<amount>.+?)\s*-\s*yield$", "Выход: {amount}"),
        (r"^(?P<amount>.+?)\s*-\s*total time$", "Общее время: {amount}"),
        (r"^(?P<amount>.+?)\s*-\s*grind size$", "Помол: {amount}"),
        (r"^(?P<amount>.+?)\s*-\s*температура$", "Температура: {amount}"),
        (r"^(?P<amount>.+?)\s*-\s*выход$", "Выход: {amount}"),
        (r"^(?P<amount>.+?)\s*-\s*общее время$", "Общее время: {amount}"),
        (r"^(?P<amount>.+?)\s*-\s*помол$", "Помол: {amount}"),
    ]
    for pattern, template in labelled_patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            return template.format(amount=match.group("amount").strip())

    ingredient_match = re.match(r"^(?P<amount>.+?)\s*-\s*(?P<label>.+)$", value)
    if ingredient_match:
        amount = ingredient_match.group("amount").strip()
        label = _translate_ingredient_label(ingredient_match.group("label"))
        inflected = _inflected_ingredient(amount, label)
        if inflected:
            return inflected
        return f"{amount} - {label}"

    value = re.sub(
        r"^(?P<amount>\d+(?:[.,]\d+)?)\s*г\s+кофейные зерна$",
        lambda m: f"{m.group('amount')} г кофейных зерен",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"^(?P<amount>\d+(?:[.,]\d+)?)\s*г\s+зерно для фильтра$",
        lambda m: f"{m.group('amount')} г зерна для фильтра",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"^(?P<amount>\d+(?:[.,]\d+)?)\s*г\s+замороженной клубники$",
        lambda m: f"{m.group('amount')} г замороженной клубники",
        value,
        flags=re.IGNORECASE,
    )
    return value


def _cleanup_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        line = _normalize_line(line)
        line = re.sub(r"^(\d+)\.\s*", r"\1) ", line)
        line = re.sub(r"(\d+\))\s*", r"\1 ", line)
        line = re.sub(r"(?<=\S)\(", " (", line)
        line = re.sub(r"\s{2,}", " ", line)
        line = re.sub(r"\s+\)", ")", line)
        line = re.sub(r"\(\s+", "(", line)
        line = re.sub(r"\s*:\s*", ": ", line)
        line = re.sub(r"(\d+): (\d+)", r"\1:\2", line)
        line = re.sub(r"\s*-\s*>", " -> ", line)
        line = re.sub(r"\(\s*(\d)", r"(\1", line)

        if re.match(r"^\d+\)\s+[а-яa-z]", line, flags=re.IGNORECASE):
            line = line[:3] + line[3:].capitalize()
        elif line:
            line = line[0].upper() + line[1:]

        lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\.\s+(\d+\))", r".\n\1", text)
    text = re.sub(r"(?<!^)\s+(\d+\))", r"\n\1", text, flags=re.MULTILINE)
    text = re.sub(
        r"(\n\d+\)\s+)([а-я])",
        lambda m: m.group(1) + m.group(2).upper(),
        text,
    )
    return text


def translate_text(value: str) -> str:
    text = value.strip()
    if not text:
        return text

    for source, target in TEXT_REPLACEMENTS:
        pattern = re.compile(re.escape(source), flags=re.IGNORECASE)
        text = pattern.sub(target, text)

    text = re.sub(r"(?<=\d)\s*gr\b", " г", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\d)\s*гр\b", " г", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\d)\s*pcs\b", " шт", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\d)\s*deg\b", " °C", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\d)\s*ml\b", " мл", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\d)\s*m\b", " мин", text)
    text = re.sub(r"(?<=\d)\s*sec\b", " сек", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\d)l\b", " л", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?P<powder>\d+(?:[.,]\d+)?)\s*г\s+какао-порошок\s*/\s*"
        r"(?P<sauce>\d+(?:[.,]\d+)?)\s*г\s+какао-соуса?",
        lambda m: f"{m.group('powder')} г какао-порошка / {m.group('sauce')} г какао-соуса",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?P<amount>\d+(?:[.,]\d+)?)\s*г\s+белый сахар\b",
        lambda m: f"{m.group('amount')} г белого сахара",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?P<amount>\d+(?:[.,]\d+)?)\s*г\s+сахар\b",
        lambda m: f"{m.group('amount')} г сахара",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"fill up cacaos' cup\s+с\s+(?P<amount>\d+(?:[.,]\d+)?)\s*г\s+горячая вода",
        lambda m: f"налейте {m.group('amount')} г горячей воды в чашку для какао",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"влейте\s+into the pitcher\s+milk\s+и\s+sugar",
        "налейте молоко и добавьте сахар в питчер",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?im)^(\d+\)\s*)?(?:add|добавьте) powder$",
        lambda m: f"{m.group(1) or ''}добавьте какао-порошок",
        text,
    )
    text = re.sub(r"\btonic\b", "тоник", text, flags=re.IGNORECASE)
    text = re.sub(r"\baperol\b", "Апероль", text, flags=re.IGNORECASE)
    text = re.sub(r"\borange slice\b", "долька апельсина", text, flags=re.IGNORECASE)
    text = re.sub(r"\badd all ingredients to a glass\b", "добавьте все ингредиенты в стакан", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwith filtered water\b", "с фильтрованной водой", text, flags=re.IGNORECASE)
    text = re.sub(r"\binto the cup\(glass\)\b", "в чашку/стакан", text, flags=re.IGNORECASE)
    text = re.sub(r"\binto the cup\b", "в чашку", text, flags=re.IGNORECASE)
    text = re.sub(r"\binto the glass\b", "в стакан", text, flags=re.IGNORECASE)
    text = re.sub(r"\bin the remaining milk\b", "в оставшееся молоко", text, flags=re.IGNORECASE)
    text = re.sub(r"\bin the espresso\b", "в эспрессо", text, flags=re.IGNORECASE)
    text = re.sub(r"\bin the milk\b", "в молоко", text, flags=re.IGNORECASE)
    text = re.sub(r"\bin\s+оставшееся молоко\b", "в оставшееся молоко", text, flags=re.IGNORECASE)
    text = re.sub(r"\bin\s+эспрессо\b", "эспрессо", text, flags=re.IGNORECASE)
    text = re.sub(r"влейте\s+in\s+", "влейте ", text, flags=re.IGNORECASE)
    text = re.sub(r"затем\s+влейте\s+in\s+", "затем влейте ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bвлейте в оставшееся молоко\b", "влейте оставшееся молоко", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdegrees\b", "градусов", text, flags=re.IGNORECASE)
    text = re.sub(r"\bprepare\b", "приготовьте", text, flags=re.IGNORECASE)
    text = re.sub(r"\badd\b", "добавьте", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpour\b", "влейте", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmix\b", "смешайте", text, flags=re.IGNORECASE)
    text = re.sub(r"\bstir\b", "перемешайте", text, flags=re.IGNORECASE)
    text = re.sub(r"\bboil\b", "вскипятите", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba kettle\b", "чайник", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwith\b", "с", text, flags=re.IGNORECASE)
    text = re.sub(r"\bglass\b", "стакан", text, flags=re.IGNORECASE)
    text = re.sub(r"\btemperature\b", "температура", text, flags=re.IGNORECASE)
    text = re.sub(r"\byield\b", "выход", text, flags=re.IGNORECASE)
    text = re.sub(r"\bgrind size\b", "помол", text, flags=re.IGNORECASE)
    text = re.sub(r"\btotal time\b", "общее время", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthen\b", "затем", text, flags=re.IGNORECASE)
    text = re.sub(r"\band\b", "и", text, flags=re.IGNORECASE)
    text = re.sub(r"латте\s*-\s*арт", "латте-арт", text, flags=re.IGNORECASE)
    text = re.sub(
        r"вскипятите чайник at (\d+) градусов с фильтрованная вода",
        r"вскипятите чайник с фильтрованной водой до \1 градусов",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\bbrew ratio\b", "соотношение заваривания", text, flags=re.IGNORECASE)
    text = re.sub(r"\bhot вода\b", "горячая вода", text, flags=re.IGNORECASE)
    text = re.sub(r"\bгорячая вода to the tea pot\b", "горячую воду в чайник", text, flags=re.IGNORECASE)
    text = re.sub(r"\bvanilla сахар\b", "ванильный сахар", text, flags=re.IGNORECASE)
    text = re.sub(r"\blemongrass\b", "лемонграсс", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcream\(yellow\)\b", "сливки (желтые)", text, flags=re.IGNORECASE)
    text = re.sub(r"\bturmeric\(куркума\)\b", "куркума", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsesame seeds on top\b", "кунжут сверху", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpop corn on top\b", "попкорн сверху", text, flags=re.IGNORECASE)
    text = re.sub(r"\bserve\b", "подавайте", text, flags=re.IGNORECASE)
    text = re.sub(r"\betching\b", "этчинг", text, flags=re.IGNORECASE)
    text = re.sub(r"\bratio\s*1:2\b", "соотношение 1:2", text, flags=re.IGNORECASE)
    text = re.sub(r"\b1 liter cherry juice\b", "1 л вишневого сока", text, flags=re.IGNORECASE)
    text = re.sub(r"\b1 sliced green apple\b", "1 зеленое яблоко, нарезанное дольками", text, flags=re.IGNORECASE)
    text = re.sub(r"\b1 sliced orange\b", "1 апельсин, нарезанный дольками", text, flags=re.IGNORECASE)
    text = re.sub(r"\b1/4 sliced lemon\b", "1/4 лимона, нарезанного дольками", text, flags=re.IGNORECASE)
    text = re.sub(r"\b0\.5 cinnamons stick \+ 2 dashes of cinnamon powder\b", "0,5 палочки корицы + 2 щепотки молотой корицы", text, flags=re.IGNORECASE)
    text = re.sub(r"\b10 г sliced имбирь\b", "10 г нарезанного имбиря", text, flags=re.IGNORECASE)
    text = re.sub(r"\b10 шт гвоздикаs\b", "10 шт гвоздики", text, flags=re.IGNORECASE)
    text = re.sub(r"\b3 drops of табаско\b", "3 капли табаско", text, flags=re.IGNORECASE)
    text = re.sub(r"\b110 sparkling wine on top\b", "110 г игристого вина сверху", text, flags=re.IGNORECASE)
    text = re.sub(r"\b20ml cherry syrup\b", "20 мл вишневого сиропа", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwhite sugar 200 г vanilla sugar 200 г\b", "200 г белого сахара\n200 г ванильного сахара", text, flags=re.IGNORECASE)
    text = re.sub(r"\b120 g белый сахар\b", "120 г белого сахара", text, flags=re.IGNORECASE)
    text = re.sub(r"\b220 g halva\b", "220 г халвы", text, flags=re.IGNORECASE)
    text = re.sub(r"\b270 g filtered hot вода \(80°C\)\b", "270 г горячей фильтрованной воды (80°C)", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcb 220 мл bottle \(closed\)\b", "бутылка колд брю 220 мл (закрытая)", text, flags=re.IGNORECASE)
    text = re.sub(r"\b4 шт of an ice\b", "4 шт льда", text, flags=re.IGNORECASE)
    text = re.sub(r"\b5 г - sea buckthorn berries\b", "5 г - ягод облепихи", text, flags=re.IGNORECASE)
    text = re.sub(r"\b170 грр - Schweppes\b", "170 г - Schweppes", text, flags=re.IGNORECASE)
    text = _cleanup_text(text)
    text = re.sub(
        r"(?im)^\d+\)\s*добавьте белый сахар to a saucepan и melt until it becomes a liquid caramel\.\s*\(important: do not bring the caramel to a state и do not let it “burn”\)$",
        "3) Добавьте белый сахар в сотейник и растопите до состояния жидкой карамели. Важно: не дайте карамели подгореть.",
        text,
    )
    text = re.sub(
        r"(?im)^\d+\)\s*добавьте белый сахар to a saucepan и melt until it reaches a liquid caramel color\.\s*\(important: do not let the caramel turn black и do not let it “burn”\)$",
        "1) Добавьте белый сахар в сотейник и растопите до жидкой карамели. Важно: не дайте карамели почернеть и подгореть.",
        text,
    )
    text = re.sub(r"(?im)^\d+\)\s*добавьте salt$", "3) Добавьте соль", text)
    text = re.sub(r"(?im)^\d+\)\s*добавьте milk и сгущенное молоко to the pitcher$", "2) Добавьте молоко и сгущенное молоко в питчер", text)
    text = re.sub(r"(?im)^\d+\)\s*влейте в молоко in the стакан$", "4) Влейте молоко в стакан", text)
    text = re.sub(r"(?im)^\d+\)\s*fill small lattes?' cup с 20 г горячая вода$", "1) Налейте 20 г горячей воды в маленькую чашку для латте", text)
    text = re.sub(r"(?im)^\d+\)\s*взбитое молоко и влейте в молоко using the latte art technique\.$", "4) Взбейте молоко паром и влейте его в стакан в технике латте-арт.", text)
    text = re.sub(r"(?im)^1 г rosemary$", "1 г розмарина", text)
    text = re.sub(r"(?im)^10 г sliced имбирь$", "10 г нарезанного имбиря", text)
    text = re.sub(r"(?im)^\d+\)\s*cook over medium heat for 10 - 15 minutes\.$", "3) Готовьте на среднем огне 10-15 минут.", text)
    text = re.sub(r"(?im)^\d+\)\s*drain into a saucepan through a sieve, cool\.$", "4) Процедите через сито в кастрюлю и остудите.", text)
    text = re.sub(r"(?im)^20 мл вишневый сироп$", "20 мл вишневого сиропа", text)
    text = re.sub(r"(?im)^110 игристое вино on top$", "110 г игристого вина сверху", text)
    text = re.sub(r"(?im)^\d+\)\s*добавьте ice, bitter, syrup, апельсиновый сок$", "1) Добавьте лед, биттер, сироп и апельсиновый сок", text)
    text = re.sub(r"(?im)^\d+\)\s*добавьте игристое вино on top$", "3) Добавьте сверху игристое вино", text)
    text = re.sub(r"(?im)^белый сахар 200 г ванильный сахар 200 г$", "200 г белого сахара\n200 г ванильного сахара", text)
    text = re.sub(r"(?im)^270 g filtered горячая вода \(80°C\)$", "270 г горячей фильтрованной воды (80°C)", text)
    text = _cleanup_text(text)
    text = re.sub(r"латте\s*-\s*арт", "латте-арт", text, flags=re.IGNORECASE)
    text = re.sub(r"(?im)^10 г sliced ginger$", "10 г нарезанного имбиря", text)
    text = re.sub(r"\.\s+важно:", ". Важно:", text)
    text = re.sub(r"\.\s+нарежьте", ". Нарежьте", text)
    return text
