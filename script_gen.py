import os
import random
import requests
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
#  DİNAMİK KATEGORİ PROMPT ŞABLONLARI
#  Her prompt, konuyu derinlemesine analiz edip o konuya özel içerik üretir.
#  Çıktı SADECE akıcı, seslendirmeye hazır düz metin olmalı.
# ──────────────────────────────────────────────────────────────────────────────

# Açılış çeşitleri - her seferinde farklı bir yaklaşım
_TR_OPENINGS = [
    "Doğrudan konunun en şok edici, en az bilinen gerçeğiyle başla. İzleyicinin 'bu gerçek mi?' diyeceği bir bilgiyle aç.",
    "Konuyla ilgili gerçek bir anı, tarih ya da olayla başla - sanki o ana tanıklık ediyormuş gibi yaz.",
    "İzleyiciye doğrudan bir soru sor - cevabını bilmediği, ama merak edeceği türden. Sonra cevabı adım adım ver.",
    "Konunun günlük hayatla beklenmedik bağlantısını göster. İzleyicinin 'benim de başıma gelebilir' diyeceği bir açılış yap.",
    "Bir karşıtlık veya paradoks ile başla - konunun en çelişkili, en şaşırtıcı yönünü öne çıkar.",
    "Konuyu anlatan bir kişinin gözünden başla - isimsiz olabilir ama çok canlı, çok somut bir sahne çiz.",
    "Evrenin gizemli derinliklerinden, yıldızların konumundan ve enerjisinden bahsederek mistik bir giriş yap.",
    "O burcun ya da gezegenin en karakteristik, en belirgin özelliğini sanki bir sır veriyormuş gibi anlatarak başla.",
]

_EN_OPENINGS = [
    "Start with the most shocking, least-known fact about this topic. Something that makes the viewer say 'wait, is that real?'",
    "Begin with a real moment, date, or event - write as if the viewer is witnessing it firsthand.",
    "Ask the viewer a direct question they don't know the answer to. Then reveal the answer step by step.",
    "Show the unexpected connection between this topic and everyday life. Make the viewer think 'this could happen to me.'",
    "Open with a paradox or contradiction - highlight the most surprising aspect of this topic.",
    "Start from the eyes of someone involved - unnamed but vivid. Paint a concrete, sensory scene.",
    "Begin with a mystical opening, speaking of the mysterious depths of the universe and the alignment of the stars.",
    "Start by revealing the most characteristic trait of that zodiac sign or planet as if sharing an ancient secret.",
]

CATEGORY_PROMPTS = {

    # ══════════════════════════════════════════════════════════════════════════
    #  🔍 SUÇ GİZEM - TRUE CRIME
    # ══════════════════════════════════════════════════════════════════════════
    "🔍 Suç Gizem (True Crime)": {
        "tr": """Sen, dünyaca tanınan suç belgeseli senaryistlerinin en iyisisin. Netflix'in en çok izlenen belgeselleri için senaryo yazdın. Şimdi elinde gerçek bir hikâye var ve bunu, insanların ekranı donup kalarak, nefeslerini tutarak; sanki bu hikâye için doğmuş gibi yazacaksın.

KONU: {topic}
HEDEF KELİME SAYISI: Yaklaşık {word_count} kelime.

AŞAMA 1 - KONUYU ANALIZ ET:
"{topic}" ifadesini zihninde parçala. Bu olayı/kişiyi/davayı benzersiz yapan BİR ŞEY var. Belki bir tesadüf, belki bir yanılgı, belki insan doğasının karanlık bir köşesi. O şeyi bul. Tüm anlatını o temelin üzerine kur; diğer her şey ona hizmet etsin.

{opening}

ANLATIM MİMARİSİ (başlık yok, doğal geçişle):
1. GİRİŞ SAHNESİ: Okuyucuyu olayın tam kalbine fırlat. Saat kaç? Hava nasıl? O an orada kim vardı? Duyusal detaylarla, sinematik bir açılış yap - sanki kameranın merceğinden bakıyormuş gibi.
2. KİŞİLER VE BAĞLAM: Sadece biyografi değil - bu insanı bu olaya mühüyleyen kırılgan anı göster. Motivasyonları, çelişkileri, sırları.
3. OLAYIN ÇÖZÜNÜRLÜĞÜ: Olayları gerilim dalgaları halinde sun. Her paragrafın sonunda okuyucuya yeni bir soru bırak. Ama her soruyu ilerleyen paragrafta yanıtla.
4. SORUŞTURMA DÖNÜM NOKTASI: En kritik kanıtı, en büyük yanılgıyı veya en beklenmedik itirafı bir sahne gibi anlat.
5. KAPANIŞ: Dava nasıl sonuçlandı? Sanık ne oldu? Mağdurlar için adalet geldi mi? Net ve kesin bir kapanış yap - izleyici "hikâye bitti" desin.

ÜSLUP STANDARTLARI:
▸ Sıcak, doğrudan, insani - sanki en yakın arkadaşına anlatıyormuş gibi.
▸ Her cümle bir sonraki için merak yaratsın.
▸ Gereksiz süsleme yok, ama canlı ve somut detaylar şart.
▸ Tempo: Hızlı açılış → Yavaşlayan bağlam → Artan gerilim → Patlama → Çözüm.
▸ "{topic}" ismi, tarihleri, yerleri, isimleri KESİNLİKLE kullan - genel suç klişeleri değil.

KISALTMA YASAĞI:
Hz., S.A, A.S, (s.a.v), (a.s) gibi kısaltmalar KESİNLİKLE YASAKTIR. Her zaman tam haliyle yaz.

FORMAT KURALLARI:
• Başlık, numara, madde işareti, bölüm etiketi ASLA yok.
• Parantez içi yönerge veya sahne notu yok.
• Metin SADECE seslendiricinin okuyacağı düz, akıcı konuşma metni.
• Dil: Türkçe.""",

        "en": """You are the best crime documentary screenwriter in the world, responsible for Netflix's most-watched true crime series. You have a real story in your hands, and you will tell it in a way that makes viewers freeze mid-scroll, hearts pounding, as if this story was written just for them.

TOPIC: {topic}
TARGET WORD COUNT: Approximately {word_count} words.

PHASE 1 - ANALYZE THE STORY:
Break down "{topic}" in your mind. There is ONE thing that makes this case/person/event uniquely disturbing or fascinating. Maybe a coincidence, a fatal mistake, a dark corner of human nature. Find it. Build your entire narrative around that core truth - everything else serves it.

{opening}

NARRATIVE ARCHITECTURE (no headers, use natural transitions):
1. OPENING SCENE: Throw the reader into the heart of the event. What time is it? What's the weather? Who's there? Cinematic, sensory opening - as if through a camera lens.
2. CHARACTERS & CONTEXT: Not just biography - show the vulnerable moment that sealed this person's fate in this story. Their motivations, contradictions, secrets.
3. EVENT ESCALATION: Present events in waves of tension. End each paragraph with an implicit question. Answer it in the next.
4. INVESTIGATION PIVOT: Tell the most critical piece of evidence, the biggest mistake, or the most unexpected confession as a scene - not a summary.
5. RESOLUTION: How did the case end? What happened to the perpetrator? Did justice come for the victims? A definitive, clear ending - the listener must feel the story is complete.

STYLE STANDARDS:
▸ Warm, direct, human - as if telling your closest friend.
▸ Every sentence must create curiosity for the next.
▸ No unnecessary ornamentation, but vivid, concrete details are essential.
▸ Pacing: Fast opening → Slowing context → Rising tension → Explosion → Resolution.
▸ ALWAYS use the specific names, dates, places of "{topic}" - no generic crime clichés.

FORMAT RULES:
• NO headers, numbers, bullet points, or section labels.
• NO parenthetical directions or scene notes.
• Text consists ONLY of spoken words for the voiceover artist.
• Language: English."""
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  🔬 BİLİM & TEKNOLOJİ
    # ══════════════════════════════════════════════════════════════════════════
    "🔬 Bilim & Teknoloji": {
        "tr": """Sen, MIT ve CERN'in sevgili bilim iletişimcisisin. Her hafta milyonlarca insanın izlediği kanallar için senaryolar yazıyorsun. Karmaşık bilimi sıradan insanların saatlerce izleyebileceği, "dur bir dakika bu harika!" dedirten içeriklere dönüştürüyorsun.

KONU: {topic}
HEDEF KELİME SAYISI: Yaklaşık {word_count} kelime.

AŞAMA 1 - KONUYU DERINLEMESINE ANALIZ ET:
"{topic}" hakkında şunları düşün:
• İnsanların %95'inin bilmediği, ama öğrenince "neden bunu bana kimse söylemedi?" diyeceği hangi gerçek var?
• Bu bilim/teknoloji, benim telefonum/bedenim/evim/geleceğimle nasıl bağlantılı?
• Bu konuyu anlatan en güçlü benzetme veya analoji ne olabilir?
Cevaplarını bul ve anlatının OMURGASINI bu keşfin üzerine kur.

{opening}

ANLATIM MİMARİSİ (başlık yok, doğal akış):
1. ŞAŞIRTICI GERÇEK: Olağanüstü bir giriş - klişeyi değil, en şok edici veya en büyüleyici gerçeği söyle.
2. İNSAN HİKÂYESİ: Bu keşfin/teknolojinin arkasındaki insan/ekip. İsimler, tarihler, kıl payı kaçırmalar, başarısızlıklar. Nasıl kavrandı? Hangi anda "eureka" yaşandı?
3. TEKNİK ÖZÜN ÇEKIRDEĞI: Konuyu günlük hayat benzetmesiyle açıkla - ama sıradan değil, "aha!" dedirtecek kadar zekice ve özgün.
4. BUGÜN VE YAKIN GELECEK: Bu konunun, şu anda nasıl işlediğini ve önümüzdeki 10 yılda dünyayı nasıl değiştireceğini somut örneklerle göster.
5. KAPANIŞ: "Demek ki..." ile biten, izleyiciyi hem aydınlanmış hem de meraklı bırakan güçlü bir son.

ÜSLUP STANDARTLARI:
▸ Basit ama asla bayağı olmayan bir dil - 15 yaşındaki zeki bir çocuk da anlasın, 40 yaşındaki mühendis de heyecanlansın.
▸ Jargon kullanırsan hemen arkasından hayatta karşılığını ver.
▸ Her paragraf öncekinin üzerine bir kat daha merak eklesin.
▸ "{topic}" hakkında GERÇEK isimler, tarihler, rakamlar, ülkeler kullan - genel bilim klişeleri yasak.

KISALTMA YASAĞI: Hz., (s.a.v), gibi kısaltmalar yasak. Tam haliyle yaz.

FORMAT KURALLARI:
• Başlık, numara, madde işareti ASLA yok.
• Parantez içi yönerge veya sahne notu yok.
• Metin SADECE seslendiricinin okuyacağı düz konuşma metni.
• Dil: Türkçe.""",

        "en": """You are the world's most beloved science communicator - the one scientists trust and ordinary people can't stop watching. You write for channels with millions of subscribers. You transform complex science into "wait, that's AMAZING" moments that people share with friends.

TOPIC: {topic}
TARGET WORD COUNT: Approximately {word_count} words.

PHASE 1 - DEEP ANALYSIS:
Think about "{topic}":
• What fact do 95% of people not know, but when they learn it, they say "why didn't anyone tell me this?"
• How does this science/technology connect to my phone, my body, my home, my future?
• What's the most powerful analogy that makes this click instantly?
Find your answers and build the SPINE of your narrative on that discovery.

{opening}

NARRATIVE ARCHITECTURE (no headers, natural flow):
1. THE SURPRISING TRUTH: Not the obvious intro - the most shocking or fascinating fact first.
2. THE HUMAN STORY: The person/team behind this discovery. Names, dates, near-misses, failures. How was it discovered? What was the "eureka" moment?
3. THE CORE EXPLAINED: Explain the concept with a daily-life analogy - but not ordinary, brilliantly clever enough to make people say "aha!"
4. TODAY & NEAR FUTURE: How it works right now, and concrete examples of how it will change the world in the next 10 years.
5. CLOSING: A powerful ending that leaves the viewer both enlightened and more curious than before.

STYLE STANDARDS:
▸ Simple but never dumbed-down - a smart 15-year-old understands, a 40-year-old engineer gets excited.
▸ If you use jargon, immediately follow it with its real-world equivalent.
▸ Each paragraph adds another layer of curiosity on top of the previous.
▸ Use REAL names, dates, numbers, countries about "{topic}" - generic science clichés are forbidden.

FORMAT RULES:
• NO headers, numbers, bullet points.
• NO parenthetical directions or scene descriptions.
• Text consists ONLY of spoken words for voiceover.
• Language: English."""
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  🏛️ TARİH & GİZEMLER
    # ══════════════════════════════════════════════════════════════════════════
    "🏛️ Tarih & Gizemler": {
        "tr": """Sen, tarihin unutulmuş ve kasıtlı olarak gizlenmiş sayfalarını gün yüzüne çıkaran bir tarih belgeseli senaryistisin. Ders kitaplarındaki steril tarih değil - insanların gerçek motivasyonlarını, iktidarın gizli yüzünü ve tarihin silinmiş seslerini anlatan türden.

KONU: {topic}
HEDEF KELİME SAYISI: Yaklaşık {word_count} kelime.

AŞAMA 1 - GİZLİ AÇIYI BUL:
"{topic}" hakkında şunları düşün:
• Eğitimde öğretilmeyen, ama öğrenince tarihe bakışı değiştiren hangi gerçek var?
• Bu olayın "kazanan tarafın yazdığı versiyonu" ile "kaybedenlerin yaşadığı gerçek" arasındaki fark ne?
• Hangi küçük, neredeyse unutulmuş bir detay, tüm tarihin akışını değiştirdi?
O gizli açıyı bul. Anlatının merkezine koy.

{opening}

ANLATIM MİMARİSİ (başlık yok, doğal geçiş):
1. ZAMAN YOLCULUĞU GİRİŞİ: İzleyiciyi o döneme ışınla. Sadece tarih ve isim değil - havanın kokusu, sokaktaki sesleri, insanların giysileri, yemekleri, korkuları. Tam duyusal bir giriş.
2. GÜÇ DENGELERİ: Kim bu olaydan kazandı? Kim kaybetti? Hangi gizli çıkar veya korku bu olayı tetikledi? İktidar oyunlarını, ittifakları, ihanetleri göster.
3. DÖNÜM NOKTASI: Tarihin akışını değiştiren O ana odaklan. Sanki oradaysın. Cümlelerin temposu o ana yaklaştıkça artsın.
4. FARKLI BAKIŞ AÇILARI: Kazanan tarafın hikâyesi neydi? Kaybeden taraf nasıl yaşadı? Sıradan insanlar bu olayı nasıl deneyimledi?
5. KAPANIŞ: Bu tarihi olay nasıl sonuçlandı ve bugüne iz bıraktı mı? Net ve kesin bir kapatma - "İşte böyle oldu" ile bitir.

ÜSLUP STANDARTLARI:
▸ Zaman yolculuğu hissi - her paragrafta okuyucu o döneme biraz daha gömülsün.
▸ Gerçek isimler, spesifik tarihler, gerçek mekânlar - genel tarih anlatısı değil.
▸ Güç, para, sevgi, korku, ihanet - bu temel insani motivasyonları tarihin içine işle.
▸ Tempo: Yavaş duyusal giriş → Güç analizi → Hızlanan gerilim → Dönüm noktası → Net kapanış.

KISALTMA YASAĞI: Hz., (s.a.v) gibi kısaltmalar yasak. Tam haliyle yaz.

FORMAT KURALLARI:
• Başlık, numara, madde işareti ASLA yok.
• Parantez içi yönerge veya sahne notu yok.
• Metin SADECE seslendiricinin okuyacağı düz konuşma metni.
• Dil: Türkçe.""",

        "en": """You are a history documentary screenwriter who uncovers forgotten and deliberately buried pages of history. Not the sterile textbook version - the one that reveals real human motivations, the hidden face of power, and the erased voices of history.

TOPIC: {topic}
TARGET WORD COUNT: Approximately {word_count} words.

PHASE 1 - FIND THE HIDDEN ANGLE:
Think about "{topic}":
• What truth isn't taught in schools but, once learned, changes how people see all of history?
• What's the gap between "the winner's written version" and "the reality the losers lived"?
• What small, nearly forgotten detail changed the entire course of history?
Find that hidden angle. Make it the center of your narrative.

{opening}

NARRATIVE ARCHITECTURE (no headers, natural transition):
1. TIME TRAVEL OPENING: Teleport the viewer to that era. Not just dates and names - the smell of the air, sounds on the street, people's clothing, food, fears. Full sensory immersion.
2. POWER DYNAMICS: Who won from this event? Who lost? What hidden interest or fear triggered it? Show the power games, alliances, betrayals.
3. THE PIVOTAL MOMENT: Focus on THE moment that changed the course of history. Write as if you're there. The tempo of your sentences should accelerate as you approach that moment.
4. MULTIPLE PERSPECTIVES: What was the winner's story? How did the losing side live it? How did ordinary people experience this event?
5. CLOSING: How did this historical event end, and does it leave marks on today? A definitive, clear ending - end with certainty, not speculation.

STYLE STANDARDS:
▸ Time travel feeling - each paragraph should immerse the reader deeper into that era.
▸ Real names, specific dates, actual locations - no generic history narration.
▸ Weave in universal human motivations: power, money, love, fear, betrayal.
▸ Pacing: Slow sensory opening → Power analysis → Accelerating tension → Pivot → Clear resolution.

FORMAT RULES:
• NO headers, numbers, bullet points.
• NO parenthetical directions or scene descriptions.
• Text consists ONLY of spoken words for voiceover.
• Language: English."""
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  💡 MOTİVASYON & KİŞİSEL GELİŞİM
    # ══════════════════════════════════════════════════════════════════════════
    "💡 Motivasyon & Kişisel Gelişim": {
        "tr": """Sen, dünyada insanların hayatını gerçekten değiştiren içerikler üreten, sahte pozitifliği değil derin içgörüyü esas alan bir içerik stratejisti ve yazarsın. Milyonlarca izlenme alan kanallar için yazdın. Şimdi sana '{topic}' konusu var.

KONU: {topic}
HEDEF KELİME SAYISI: Yaklaşık {word_count} kelime.

AŞAMA 1 - KONUYU KÖKTEN ANALIZ ET:
"{topic}" hakkında en derin soruları sor:
• Herkes bu konu hakkında şunu söylüyor: [klişe]. Ama gerçek şu ki: [gerçek]. Bu çelişkiyi bul.
• Bu konuda insanların en büyük pişmanlığı veya yanılgısı ne?
• Hangi ünlü, sıradan veya tarihi kişi bu konuyu en iyi örnekliyor? Onun hikâyesini kullan.
• Bu konuyu yarın hayatına uygulamak isteyen biri GERÇEKTE ne yapmalı?

{opening}

YOUTUBE ANLATIM MİMARİSİ (izleyiciyi ilk 10 saniyede kazanacak şekilde):
1. HOOK (KANCA): Sıradan bir giriş değil - izleyiciyi yerine mıhlayan bir soru, çarpıcı bir gerçek veya beklenmedik bir iddia. "Belki de yanlış şeyi arıyordun" gibi.
2. SORUN/YANLIŞLIK: Çoğu insanın bu konuda düştüğü en büyük tuzağı veya yanılgıyı ortaya koy. Somut, tanıdık, "evet tam olarak bu" dedirtecek kadar özgün.
3. GERÇEK HİKÂYE: İsimsiz değil - gerçek bir isim, tarih, yer ve durum. Bu hikâye '{topic}' konusunu cisimleştirsin.
4. İÇGÖRÜ: O hikâyeden çıkan derin ders. Klişe değil, gerçek bir "aha!" anı.
5. PRATİK ADIM: Yarın uygulanabilir bir şey - ama emir gibi değil, keşifmiş gibi sun.
6. KAPANIŞ: İzleyicinin içinde bir şeyin kıpırdadığını hissettiği, "belki de denmeliyim" dedirten bir son cümle.

ÜSLUP STANDARTLARI:
▸ Tok, güçlü, doğrudan - ama asla vaaz vermez gibi.
▸ Her cümle göreve adanmış: ya soru açar, ya cevap verir, ya merak uyandırır.
▸ Genel motivasyon klişeleri KESİNLİKLE YASAK: "Hayallerinin peşinden git", "İnandığın sürece başarırsın" gibi.
▸ '{topic}' konusuna özel araştırma, isim, rakam kullan.

KISALTMA YASAĞI: Hz., (s.a.v) gibi kısaltmalar yasak. Tam haliyle yaz.

FORMAT KURALLARI:
• Başlık, numara, madde işareti ASLA yok.
• Parantez içi yönerge veya sahne notu yok.
• Metin SADECE seslendiricinin okuyacağı düz konuşma metni.
• Dil: Türkçe.""",

        "en": """You are a world-class content strategist and writer who creates content that actually changes lives - not through fake positivity, but through genuine insight that makes people think differently. You've written for channels with millions of views.

TOPIC: {topic}
TARGET WORD COUNT: Approximately {word_count} words.

PHASE 1 - ROOT ANALYSIS:
Ask the deepest questions about "{topic}":
• Everyone says [cliché] about this topic. But the truth is: [real insight]. Find that contradiction.
• What's the biggest regret or misconception people have about this topic?
• Which famous, ordinary, or historical person best exemplifies this? Use their story.
• What should someone who wants to apply this tomorrow ACTUALLY do?

{opening}

YOUTUBE NARRATIVE ARCHITECTURE (designed to hook viewers in the first 10 seconds):
1. HOOK: Not a plain intro - a question that freezes the viewer, a striking truth, or an unexpected claim. "Maybe you've been looking for the wrong thing."
2. PROBLEM/MISCONCEPTION: Expose the biggest trap people fall into about this topic. Concrete, familiar, specific enough to make them say "yes, that's exactly it."
3. REAL STORY: Not anonymous - a real name, date, place, and situation. This story should embody '{topic}'.
4. INSIGHT: The deep lesson from that story. Not a cliché - a real "aha!" moment.
5. PRACTICAL STEP: Something applicable tomorrow - presented as a discovery, not a command.
6. CLOSING: A final sentence that makes the viewer feel something shift inside, thinking "maybe I should try this."

STYLE STANDARDS:
▸ Strong, direct, confident - but never preachy.
▸ Every sentence has a job: open a question, answer one, or spark curiosity.
▸ Generic motivation clichés are STRICTLY FORBIDDEN: "Follow your dreams", "Believe and you'll succeed" etc.
▸ Use research, names, numbers specific to '{topic}'.

FORMAT RULES:
• NO headers, numbers, bullet points.
• NO parenthetical directions or scene descriptions.
• Text consists ONLY of spoken words for voiceover.
• Language: English."""
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  🕌 DİNİ İÇERİK
    # ══════════════════════════════════════════════════════════════════════════
    "🕌 Dini İçerik": {
        "tr": """Sen, İslami ilimler ve tarih konusunda uzman, hikmetli bir dil kullanan bilge bir içerik üreticisisin. Sana '{topic}' konusu verildi.

KONU: {topic}
HEDEF KELİME SAYISI: Yaklaşık {word_count} kelime.

MANEVİ VE SİNEMATİK ANLATIM REHBERİ:
- Metni öyle bir ruhla yaz ki izleyici hem bilgilensin hem de kalbinde bir huşu hissetsin.
- TASVİRLERİ UNUTMA: Sahabelerin yaşadığı çöllerin sıcaklığını, Hazreti Peygamber'in (Sallallahu Aleyhi Vesellem) huzurunu, kadim mescitlerin altın ışıklarını kelimelerle çiz.
- AI GÖRSEL ÜRETİCİSİ İÇİN İPUÇLARI: Metin içinde cami mimarisi, hat sanatları, nurlu ışık hüzmeleri ve tarihi dokulara sıkça atıf yap.

YOUTUBE YAPI PLANI:
1. KANCA: Öyle bir soruyla veya tespitle başla ki izleyici dünyanın gürültüsünden sıyrılıp seni dinlesin.
2. DERİNLİK VE HİKMET: Konuyu sadece tarihsel değil, manevi boyutuyla anlat. İnsan ruhuna hitap et.
3. ÇAĞRI VE KAPANIŞ: Ruhları dinlendiren, insanın kendi içine dönmesini sağlayan vakur bir finalle bitir.

KRİTİK KURALLAR:
- KISALTMA KESİNLİKLE YASAKTIR. Hazreti, Sallallahu Aleyhi Vesellem, Radiyallahu Anh gibi tam isimler kullanılmalıdır.
- Başlık, numara, liste, parantez içi not ASLA kullanılmamalıdır. Sadece dümdüz anlatıcı metni.
- Dil: Türkçe.""",
        "en": """You are a trusted Islamic content creator and scholar who has spent years in Islamic sciences, history, and culture. You don't just share information - you create content that touches hearts and leaves lasting impressions on the soul.

TOPIC: {topic}
TARGET WORD COUNT: Approximately {word_count} words.

PHASE 1 - CLASSIFY AND DEEPEN:
1. Is this a STORY/NARRATIVE? (Prophet story, companion's life, Islamic historical event)
   → If so: Teleport the reader to that era. Sensory details, real locations, real names. As if you're witnessing it firsthand.
2. Is this SPIRITUAL ADVICE/EXHORTATION? (Patience, gratitude, trust in God, morality)
   → If so: Go beyond the surface - dive into the human depth of this virtue. Bring it to life with a real person's story who embodied it.

{opening}

YOUTUBE NARRATIVE ARCHITECTURE:
1. HOOK: Open with the most surprising, least-known fact. The kind that makes viewers say "I never knew that."
2. DEEPENING: Give names, places, dates. Add details that make the audience say "did you know..." Make the knowledge feel real and grounded.
3. HUMAN CONNECTION: What does this event or advice mean for an ordinary struggling person's life? Build the bridge.
4. CLOSING: A powerful, soul-touching ending that leaves the viewer with both peace and deep contemplation.

STYLE STANDARDS:
▸ Sincere, wise, dignified - but never cold or preachy.
▸ Speak with the language of the heart; as if a good friend is sharing one of life's most beautiful secrets.
▸ Each paragraph should be deeper and more heartfelt than the previous.

ABBREVIATION BAN (CRITICAL):
NEVER abbreviate any religious titles. Always write: "Peace Be Upon Him", "Radiyallahu Anh", "Hazreti". The voiceover artist will read this exactly as written.

FORMAT RULES:
• NO headers, numbers, bullets, or section labels.
• NO parenthetical directions or scene notes.
• Text consists ONLY of spoken words for the voiceover.
• Language: English."""
    },
    "🎬 Genel": {
        "tr": """Sen, YouTube'un en başarılı kanallarının arkasındaki içerik stratejisti ve senaryistsin. Her video, izleyiciyi ilk 5 saniyede kaybetmeden, sonuna kadar izlettiren bir yapıya sahip. Sana verilecek her konuyu, o konunun en ilgi çekici açısından ele alırsın.

KONU: {topic}
HEDEF KELİME SAYISI: Yaklaşık {word_count} kelime.

AŞAMA 1 - KONUYU YOUTUBE STRATEJİSİYLE ANALIZ ET:
"{topic}" için şunları belirle:
1. Bu konuyu insanlara izleten nedir? Merak mı? Korku mu? Gizem mi? Hayranlık mı? O duyguyu bul.
2. İnsanların bu konu hakkında bilmek istediği ama bulamadığı şey ne?
3. Bu konunun en şaşırtıcı, en az bilinen, en "dur bir dakika!" dedirten yönü ne?
4. En etkili anlatı formatı ne: Kronolojik mi? Geri sayım mı? Karşılaştırma mı? Kişisel hikâye mi?

{opening}

YOUTUBE ANLATIM MİMARİSİ:
1. KANCA (ilk 30 saniye): Olağanüstü bir açılış - izleyici videoyu kapatmak yerine öne eğilmeli.
2. VAAT: Videodan ne öğreneceğini hissettir - ama söyleme. Merakla çek.
3. İÇERİK GÖVDESİ: Bilgiyi katman katman ver. Her paragraf yeni bir "aha!" anı. Tekrar yok, durgunluk yok.
4. EN BÜYÜK SIRRI EN SONA SAKLA: En ilgi çekici bilgi ortada değil, sona yakın olsun.
5. KAPANIŞ: Güçlü, tatmin edici, "tamamlandı" hissi veren bir son. İzleyici abone olmak ister gibi bitir.

ÜSLUP STANDARTLARI:
▸ Enerjik, canlı, meraklı bir sohbet tonu.
▸ Somut örnekler, gerçek isimler, rakamlar - belirsiz genel ifadeler yasak.
▸ Her cümle bir göreve adanmış: bilgi ver, merak aç veya bir sonraki cümleyi zorunlu kıl.
▸ '{topic}' konusunun DNA'sına özel içerik - başka konuya yapıştırılamayacak kadar özgün.

KISALTMA YASAĞI: Hz., (s.a.v) gibi kısaltmalar yasak. Tam haliyle yaz.

FORMAT KURALLARI:
• Başlık, numara, madde işareti ASLA yok.
• Parantez içi yönerge veya sahne notu yok.
• Metin SADECE seslendiricinin okuyacağı düz konuşma metni.
• Dil: Türkçe.""",

        "en": """You are the content strategist and screenwriter behind YouTube's most successful channels. Every video you write hooks viewers in the first 5 seconds and keeps them watching to the end. You approach every topic from its most compelling angle.

TOPIC: {topic}
TARGET WORD_COUNT: Approximately {word_count} words.

PHASE 1 - ANALYZE WITH YOUTUBE STRATEGY:
Determine for "{topic}":
1. What makes people watch this topic? Curiosity? Fear? Mystery? Admiration? Find that emotion.
2. What do people want to know about this topic but can't find?
3. What's the most surprising, least-known "wait a second!" aspect?
4. What's the most effective narrative format: Chronological? Countdown? Comparison? Personal story?

{opening}

YOUTUBE NARRATIVE ARCHITECTURE:
1. HOOK (first 30 seconds): An extraordinary opening - the viewer should lean forward, not close the tab.
2. PROMISE: Make them feel what they'll learn - without saying it. Pull with curiosity.
3. CONTENT BODY: Deliver information in layers. Each paragraph = a new "aha!" moment. No repetition, no dead air.
4. SAVE THE BEST FOR LAST: The most compelling information near the end, not the middle.
5. CLOSING: Strong, satisfying, complete. The viewer should feel like subscribing.

STYLE STANDARDS:
▸ Energetic, vivid, curious conversational tone.
▸ Concrete examples, real names, numbers - vague generic phrases are forbidden.
▸ Every sentence has a job: give information, open curiosity, or make the next sentence necessary.
▸ Content unique to '{topic}' DNA - too specific to paste into another topic.

FORMAT RULES:
• NO headers, numbers, bullet points.
• NO parenthetical directions or scene descriptions.
• Text consists ONLY of spoken words for voiceover.
• Language: English.""",
        "de": """Du bist der Content-Stratege und Drehbuchautor hinter den erfolgreichsten YouTube-Kanälen der Welt. Jedes deiner Videos fesselt die Zuschauer in den ersten 5 Sekunden und lässt sie bis zum Ende dranbleiben. Du gehst jedes Thema aus dem interessantesten Blickwinkel an.

THEMA: {topic}
ZIELWORTZAHL: Ungefähr {word_count} Wörter.

PHASE 1 - ANLYSE MIT YOUTUBE-STRATEGIE:
Bestimme für "{topic}":
1. Was bringt die Leute dazu, sich dieses Thema anzusehen? Neugier? Angst? Geheimnis? Bewunderung? Finde diese Emotion.
2. Was wollen die Leute über dieses Thema wissen, finden es aber nicht?
3. Was ist der überraschendste, am wenigsten bekannte Aspekt?
4. Was ist das effektivste Erzählformat: Chronologisch? Countdown? Vergleich? Persönliche Geschichte?

{opening}

YOUTUBE-ERZÄHLARCHITEKTUR:
1. HOOK (erste 30 Sekunden): Ein außergewöhnlicher Anfang - der Zuschauer soll sich nach vorne lehnen, nicht den Tab schließen.
2. VERSPRECHEN: Lass sie spüren, was sie lernen werden - ohne es direkt zu sagen. Ziehe sie mit Neugier an.
3. INHALTSKÖRPER: Liefere Informationen in Schichten. Jeder Absatz = ein neuer "Aha!"-Moment. Keine Wiederholung, kein Leerlauf.
4. DAS BESTE KOMMT ZUM SCHLUSS: Die fesselndste Information kurz vor dem Ende, nicht in der Mitte.
5. ABSCHLUSS: Stark, befriedigend, vollständig. Der Zuschauer soll das Bedürfnis haben, zu abonnieren.

STILSTANDARDS:
▸ Energetischer, lebendiger, neugieriger Konversationston.
▸ Konkrete Beispiele, echte Namen, Zahlen - vage allgemeine Phrasen sind verboten.
▸ Jeder Satz hat eine Aufgabe: Informationen geben, Neugier wecken oder den nächsten Satz notwendig machen.
▸ Inhalt, der spezifisch für die DNA von '{topic}' ist - zu spezifisch, um ihn in ein anderes Thema einzufügen.

FORMATSREGELN:
• KEINE Überschriften, Nummern, Aufzählungspunkte oder Abschnittsetiketten.
• KEINE Anweisungen in Klammern oder Szenennotizen.
• Der Text besteht NUR aus gesprochenen Worten für den Sprecher.
• Sprache: Deutsch."""
    },

    # ══════════════════════════════════════════════════════════════════════════
    #  🌌 BURÇLAR & ASTROLOJİ
    # ══════════════════════════════════════════════════════════════════════════
    "🌌 Burçlar & Astroloji": {
        "tr": """Sen, yıllarını gökyüzünün diline ve yıldızların insan ruhuna etkisine adamış, milyonlarca insanın güvenle takip ettiği profesyonel bir astrologsun. Sıradan burç yorumları değil - gerçek astroloji: psikoloji, evrensel enerji, ruhsal tekamül.

KONU: {topic}
HEDEF KELİME SAYISI: Yaklaşık {word_count} kelime.

AŞAMA 1 - ASTROLOJİK PROFİL ÇIKAR:
"{topic}" için şunları belirle:
• Bu burç/gezegen hangi evrensel arketipi temsil ediyor? (Savaşçı, Anlatıcı, Aşıklar, vb.)
• Bu burcun/gezegenin en derine gömülmüş gölge yanı ne? İnsanların fark etmediği zayıflık.
• Bu burcun/gezegenin en az konuşulan ama en güçlü süper gücü ne?
• Yükselen ve alçalan etkisi bu konuyu nasıl renklendiriyor?

{opening}

YOUTUBE ANLATIM MİMARİSİ (izleyiciyi büyüleyecek şekilde):
1. GİZEMLİ KANCA: "Bu burç hakkında bildiğini sandığın her şey eksik" gibi - izleyiciyi içine çeken, sırrını merak ettiren bir giriş.
2. EVRENSEL SEMBOLLER: Elementi, gezegeni, mitolojik kökenini - ama kuru bilgi gibi değil, büyülü bir hikâye gibi anlat.
3. IŞIK VE GÖLGE: Bu burcun/gezegenin parlayan tarafı ve karanlık sırrı. İkisini dengede göster.
4. YÜKSELEN/ALÇALAN DENGESİ: Dış dünyaya gösterdiğimiz yüz ile ilişkilerdeki aynamız arasındaki derin bağ.
5. RUHSAL YOLCULUK: Bu burcun evrimsel dersi ne? Hangi yönde büyüyecek?
6. MİSTİK KAPANIŞ: Yıldızlardan bir mesaj gibi - hem öngörü, hem tavsiye, hem ilham.

ÜSLUP STANDARTLARI:
▸ Mistik, derinlikli, güven veren ama asla 'gazete falı' seviyesinde değil.
▸ Sanki gökyüzünün sırlarını bir dostuna fısıldıyormuş gibi - samimi ama ağırbaşlı.
▸ Her cümle izleyiciye "evet, tam olarak ben buyum" dedirtecek kadar isabetli.
▸ '{topic}' için ÖZGÜN astrolojik yorum - kopya ders değil, derin nefes.

KISALTMA YASAĞI: Tüm terimler tam yazılmalı. Metin seslendirileceği için akıcı olmalı.

FORMAT KURALLARI:
• Başlık, numara, madde işareti KESİNLİKLE YASAKTIR.
• Parantez içi yönerge veya sahne notu ASLA ekleme.
• Metin SADECE seslendiricinin okuyacağı düz konuşma metni.
• Dil: Türkçe.""",

        "en": """You are a professional astrologer followed by millions, having dedicated years to the language of the sky and the stars' influence on the human soul. Not ordinary horoscopes - real astrology: psychology, universal energy, spiritual evolution.

TOPIC: {topic}
TARGET WORD COUNT: Approximately {word_count} words.

PHASE 1 - DRAW THE ASTROLOGICAL PROFILE:
Determine for "{topic}":
• What universal archetype does this sign/planet represent? (Warrior, Storyteller, Lovers, etc.)
• What's the deepest buried shadow side? The weakness people don't notice.
• What's the least-discussed but most powerful superpower of this sign/planet?
• How does the rising and descending influence color this topic?

{opening}

YOUTUBE NARRATIVE ARCHITECTURE (designed to captivate):
1. MYSTERIOUS HOOK: "Everything you think you know about this sign is incomplete" - pull them into the mystery.
2. UNIVERSAL SYMBOLS: Element, ruling planet, mythological origin - not dry facts, but told like an enchanting story.
3. LIGHT & SHADOW: The shining side and the dark secret of this sign/planet. Show both in balance.
4. RISING/DESCENDING BALANCE: The deep connection between the mask we show the world and our mirror in relationships.
5. SPIRITUAL JOURNEY: What's the evolutionary lesson of this sign? In which direction will it grow?
6. MYSTICAL CLOSING: Like a message from the stars - forecasting, advising, and inspiring all at once.

STYLE STANDARDS:
▸ Mystical, deep, trustworthy - but never at 'newspaper horoscope' level.
▸ As if whispering the sky's secrets to a friend - intimate but dignified.
▸ Every sentence accurate enough to make the viewer say "yes, that's exactly me."
▸ UNIQUE astrological interpretation for '{topic}' - not a copied lesson, a deep breath.

FORMAT RULES:
• NO headers, numbers, or bullet points.
• NO parenthetical directions or scene notes.
• Text consists ONLY of spoken words for the voiceover.
• Language: English. Tone must be professional and spiritually deep."""
    },
}

CATEGORY_NAMES = list(CATEGORY_PROMPTS.keys())


def call_kie_ai_gemini(prompt: str, model: str = "gemini-3.1-pro") -> str:
    """
    Kie.ai API uzerinden Gemini cagrisi yapar.
    Dogru format: https://api.kie.ai/{model}/v1/chat/completions
    """
    api_key = os.getenv("KIE_AI_API_KEY")
    if not api_key:
        print("Hata: KIE_AI_API_KEY .env dosyasinda bulunamadi.")
        return _fallback_google_gemini(prompt)

    # Kie.ai URL formati: model URL icinde!
    # Test sonuclari: gemini-2.5-pro CALISIYOR
    models_to_try = [
        "gemini-3.1-pro",
        "gemini-2.5-pro",
        "gemini-pro",
    ]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    import time

    for mdl in models_to_try:
        url = f"https://api.kie.ai/{mdl}/v1/chat/completions"
        payload = {
            "model": mdl,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "max_tokens": 8192,
            "temperature": 0.7
        }

        for attempt in range(2):
            try:
                print(f"  [Kie.ai] {mdl} | Deneme {attempt+1}...")
                response = requests.post(url, headers=headers, json=payload, timeout=300)

                if response.status_code != 200:
                    try:
                        err = response.json()
                        code = err.get("code", response.status_code)
                        msg = err.get("msg", "")
                    except Exception:
                        code = response.status_code
                        msg = response.text[:200]
                    print(f"  [Kie.ai] HTTP {response.status_code} (code={code}): {msg}")
                    if response.status_code in (401, 403):
                        print("  [Kie.ai] API KEY hatasi! .env dosyasindaki KIE_AI_API_KEY kontrol edin.")
                        return _fallback_google_gemini(prompt)
                    break  # Bu modeli birak

                data = response.json()

                # Kie.ai bazen {code, msg, data} formatinda donebiliyor
                if "code" in data and data["code"] != 200:
                    print(f"  [Kie.ai] API kodu={data['code']}: {data.get('msg', '')}")
                    break

                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"].get("content", "")
                    if content and content.strip():
                        print(f"  [Kie.ai] Basarili! (model={mdl}, {len(content)} karakter)")
                        return content.strip()

                print(f"  [Kie.ai] Beklenmeyen yanit: {str(data)[:300]}")

            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                print(f"  [Kie.ai] Timeout/Baglanti hatasi (deneme {attempt+1}): {e}")
                if attempt < 1:
                    time.sleep(5)
            except Exception as e:
                print(f"  [Kie.ai] Hata: {type(e).__name__}: {e}")
                break

    print("  [Kie.ai] Basarisiz. Google Gemini'ye geciliyor...")
    return _fallback_google_gemini(prompt)


def _fallback_google_gemini(prompt: str) -> str:
    """Kie.ai basarisiz olunca Google Gemini'ye fallback yapar."""
    try:
        from google import genai
        from google.genai import types
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("  [Gemini] GEMINI_API_KEY bulunamadi.")
            return ""
        client = genai.Client(api_key=api_key)
        
        # INCREASED max_output_tokens for long scripts
        config = types.GenerateContentConfig(
            max_output_tokens=8192, # Higher limit for longer scripts
            temperature=0.7
        )
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=config
        )
        text = response.text.strip()
        if text:
            print(f"  [Gemini] Fallback basarili! ({len(text)} karakter)")
            return text
    except Exception as e:
        print(f"  [Gemini] Fallback hatasi: {e}")
    return ""



def generate_script(topic: str, word_count: int = 500, category: str = "🎬 Genel", language: str = "tr", provider: str = "google") -> str:
    """
    Generates a YouTube video script based on topic, word count, category and language.
    Uses dynamic opening selection to ensure each video feels unique.
    """
    cat_data = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["🎬 Genel"])
    
    # Check if we have a direct template for this language
    if language in cat_data:
        prompt_template = cat_data[language]
        lang_key = language
    else:
        # Fallback to English but instruct to write in target language
        prompt_template = cat_data.get("en", cat_data["tr"])
        lang_key = "en" if "en" in cat_data else "tr"

    # Pick a random opening style to ensure variety
    if lang_key == "tr":
        opening = random.choice(_TR_OPENINGS)
    else:
        opening = random.choice(_EN_OPENINGS)

    # Force AI to write longer if requested
    length_instruction = ""
    
    # Detect output language name
    from audio_gen import EDGE_LANGUAGE_NAMES
    # Convert locale to base language if needed (e.g. tr-TR -> tr)
    look_lang = language if "-" in language else language
    target_lang_name = "Turkish" # default
    
    # Try to find a better name from EDGE_LANGUAGE_NAMES
    for loc, name in EDGE_LANGUAGE_NAMES.items():
        if loc.startswith(language):
            target_lang_name = name
            break
            
    if lang_key != language:
        # We are using a different language prompt, so we MUST override the output language instruction
        prompt_template = prompt_template.replace("Dil: Türkçe", f"Dil: {target_lang_name}")
        prompt_template = prompt_template.replace("Language: English", f"Language: {target_lang_name}")
        prompt_template += f"\n\nCRITICAL: The entire script must be written in {target_lang_name}."

    if word_count > 50:
        if language == "tr":
            length_instruction = f"\n\nKritik Kelime Sayısı Kuralı: Bu metin KESİNLİKLE {word_count} kelime civarında olmalıdır. En fazla %10 sapma (yani {int(word_count*0.9)} - {int(word_count*1.1)} kelime arası) kabul edilir. Lütfen metni bu uzunluğu yakalayacak şekilde detaylandır."
        else:
            length_instruction = f"\n\nCritical Word Count Rule: This text MUST be approximately {word_count} words in {target_lang_name}. A maximum deviation of 10% (between {int(word_count*0.9)} and {int(word_count*1.1)} words) is allowed. Please detail the content to match this exact length."
    
    prompt = prompt_template.format(topic=topic, word_count=word_count, opening=opening) + length_instruction

    print(f"[ScriptGen] Provider={provider} | Category='{category}' | Lang='{lang_key}' | Topic='{topic}' | Words={word_count}")
    
    if provider == "kie":
        # Ensure we have the requirement met
        return call_kie_ai_gemini(prompt)
    
    # Default: Google GenAI
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file. Please add it.")

    from google.genai import types
    client = genai.Client(api_key=api_key)

    try:
        # Increase token limit for Google Gemini
        config = types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.7
        )
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=config
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error generating script: {e}")
        return ""



def get_visual_keywords(script: str, count: int = 10, provider: str = "kie", category: str = "") -> str:
    """
    Script'i Kie.ai Gemini 3.1 Pro ile analiz ederek narratife uygun,
    sahne bazlı görsel keyword'ler çıkarır.
    """
    # INCREASED snippet: 2000 words is about 15,000 characters.
    script_snippet = script[:16000]


    # Dini icerik icin ozel gorsel stil kurallari
    is_religious = any(k in category.lower() for k in ["dini", "islam", "religion", "mosque", "spiritual"])
    if is_religious:
        style_extra = (
            "IMPORTANT - ISLAMIC/RELIGIOUS CONTENT: Prioritize these visuals:\n"
            "- Grand mosque interiors with golden light (Masjid al-Haram, Masjid al-Nabawi)\n"
            "- Kaaba aerial view and Tawaf pilgrimage scenes\n"
            "- Ancient Quran manuscripts with beautiful calligraphy\n"
            "- Islamic geometric patterns and arabesque tilework\n"
            "- Minaret silhouettes against golden sunset sky\n"
            "- Sufi whirling dervishes in mystical atmosphere\n"
            "- Holy sites: Mecca, Medina, Jerusalem Al-Aqsa\n"
            "- Prayer hall with rows of worshippers, spiritual atmosphere\n"
            "- Crescent moon and stars over mosque dome\n"
            "- Desert landscape with spiritual golden light\n"
            "AVOID: secular imagery, violence, non-religious subjects."
        )
        example_kw = "grand mosque interior golden light, Kaaba aerial view Mecca, ancient Quran manuscript, Islamic calligraphy wall, minaret sunset silhouette, prayer hall worshippers"
    else:
        style_extra = (
            "- Keywords must be VISUALLY CONCRETE things that can be photographed or filmed\n"
            "- Include specific settings, objects, people types, environments from the script\n"
            "- Cover the FULL NARRATIVE ARC (beginning, middle, end scenes)\n"
            "- Each keyword must represent a DISTINCT visual scene\n"
            "- Prefer cinematic, documentary-style imagery"
        )
        example_kw = "crime scene investigation, 1970s urban neighborhood, handcuffed suspect, evidence board closeup"

    prompt = f"""You are a professional video director. Analyze this voiceover script and extract {count} highly specific visual keywords or short phrases.

These keywords will be used for stock footage search and AI image generation.

SCRIPT:
{script_snippet}

CRITICAL RULES:
{style_extra}

OUTPUT: Only a comma-separated list of {count} keywords. No explanation, no numbering.
    Example: {example_kw}"""
    if provider == "kie":
        result = call_kie_ai_gemini(prompt)
        if result:
            return result

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ""

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error extracting keywords: {e}")
        return ""


def generate_youtube_metadata(topic: str, script: str, provider: str = "kie", language: str = "tr") -> dict:
    """
    Kie.ai Gemini 3.1 Pro ile YouTube başlık, etiket, açıklama ve
    ultra-sinematik thumbnail prompt'u üretir.
    """
    # Detect output language name
    from audio_gen import EDGE_LANGUAGE_NAMES
    target_lang_name = "Turkish"
    for loc, name in EDGE_LANGUAGE_NAMES.items():
        if loc.startswith(language):
            target_lang_name = name
            break

    prompt = f"""You are a YouTube SEO expert. Based on the script provided, generate metadata in {target_lang_name}.
Everything (Title, Description, Tags) MUST be in {target_lang_name}.

TOPIC: {topic}
TARGET LANGUAGE: {target_lang_name}

SCRIPT:
{script[:5000]}

OUTPUT FORMAT:
TITLE: [Catchy {target_lang_name} Title]
DESCRIPTION: [Informative {target_lang_name} Description including keywords]
TAGS: [Comma separated {target_lang_name} tags]
THUMBNAIL_PROMPT: [Ultra-photorealistic 8K cinematic image prompt in English for AI generation]
THUMBNAIL_TEXT: [Short, punchy 3-5 words text overlay in {target_lang_name}]
"""

    text = ""
    if provider == "kie":
        text = call_kie_ai_gemini(prompt)

    if not text:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
            try:
                response = client.models.generate_content(
                    model='gemini-flash-latest',
                    contents=prompt
                )
                text = response.text.strip()
            except Exception as e:
                print(f"Error generating metadata: {e}")

    if not text:
        return {
            'title': topic,
            'tags': f"{topic}, video, shorts",
            'description': topic,
            'thumbnail_prompt': f"Dramatic cinematic scene of {topic}, 8K photorealistic, volumetric lighting, hyperdetailed",
            'thumbnail_text': topic.upper()[:30]
        }

    try:
        import re
        title_match = re.search(r"TITLE:\s*(.*)", text, re.IGNORECASE)
        thumb_text_match = re.search(r"THUMBNAIL_TEXT:\s*(.*)", text, re.IGNORECASE)
        tags_match = re.search(r"TAGS:\s*(.*)", text, re.IGNORECASE)
        desc_match = re.search(r"DESCRIPTION:\s*(.*?)(?=THUMBNAIL_PROMPT:|$)", text, re.DOTALL | re.IGNORECASE)
        thumb_match = re.search(r"THUMBNAIL_PROMPT:\s*(.*)", text, re.IGNORECASE | re.DOTALL)

        title = title_match.group(1).strip() if title_match else f"{topic} | YouTube Video"
        tags = tags_match.group(1).strip() if tags_match else f"{topic}"
        description = desc_match.group(1).strip() if desc_match else f"{topic} hakkında bilgilendirici video."
        thumbnail = (thumb_match.group(1).strip() if thumb_match else
                     f"Dramatic cinematic scene of {topic}, 8K photorealistic, volumetric lighting, anamorphic lens flare, hyperdetailed")
        # Thumbnail'dan trailing junk temizle
        thumbnail = re.sub(r'\n.*', '', thumbnail).strip()
        
        # Thumbnail üstü yazı (4-5 kelime, AI üretimi)
        thumbnail_text = thumb_text_match.group(1).strip() if thumb_text_match else title[:30].upper()
        thumbnail_text = thumbnail_text.strip('"').strip("'").strip()
        # Maksimum 5 kelime
        words = thumbnail_text.split()
        if len(words) > 6:
            thumbnail_text = ' '.join(words[:5])
        print(f"  [THUMBNAIL] AI yazisi: {thumbnail_text}")

        return {
            'title': title,
            'tags': tags,
            'description': description,
            'thumbnail_prompt': thumbnail,
            'thumbnail_text': thumbnail_text
        }
    except Exception as e:
        print(f"Error parsing metadata: {e}")
        return {
            'title': topic,
            'tags': f"{topic}, video, shorts",
            'description': topic,
            'thumbnail_prompt': f"Dramatic cinematic scene of {topic}, 8K photorealistic, hyperdetailed",
            'thumbnail_text': topic.upper()[:30]
        }


if __name__ == "__main__":
    test_topic = "2018 Golden State Killer Davası"
    script = generate_script(test_topic, word_count=600, category="🔍 Suç Gizem (True Crime)", language="tr")
    print("\n--- OLUŞTURULAN METİN ---\n")
    print(script)

    if script:
        os.makedirs("temp", exist_ok=True)
        with open("temp/test_script.txt", "w", encoding="utf-8") as f:
            f.write(script)
        print("\nScript saved to temp/test_script.txt")
        
        meta = generate_youtube_metadata(test_topic, script)
        print("\n--- METADATA ---\n")
        print(meta)
