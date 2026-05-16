# Utbildningsmodul: Säker frånkoppling, uppmätning och installation

## 1. Säker frånkoppling och identifiering i elcentralen  

* Det första steget är alltid att lokalisera rätt matning i gruppcentralen och säkerställa att rätt säkringar bryts.  
* Leta upp aggregatet i gruppförteckningen, men tänk på att märkningen kan vara gammal eller missvisande.  
* Om FTX-aggregatet är avsäkrat med tre säkringar (tre porslinsproppar eller en trepolig dvärgbrytare) är det med största sannolikhet en trefasmaskin.  
* Trefas är vanligt i aggregat som har inbyggda elektriska värmebatterier.  
* Varning för noll-fällan: Äldre trefasmaskiner byggdes ofta för ren 400V och saknade därmed neutralledare (nolla).  
* Det är ett absolut krav att noggrant mäta om det faktiskt finns en nolla (vanligtvis blå ledare) framdragen till säkerhetsbrytaren.  
* Utan en nolla kan punkten inte konverteras till ett 230V-uttag, och då måste en underentreprenör (UE) anlitas.  
* Skruva ur smältsäkringarna helt och hållet och ta med propparna i fickan för säker frånskiljning.  
* Om dvärgbrytare används ska dessa slås av och helst låsas eller märkas tydligt med tejp.  
* Slå därefter av säkerhetsbrytaren vid själva aggregatet.

## 2. Alliancesystemet – Spöket från köket  

* I hus byggda från 70-talet fram till 90-talet är Alliancesystem mycket vanliga, vilket innebär att tak- eller vindsfläkten styrs från spiskåpan i köket.  
* Köksfläkten ligger nästan alltid på en annan gruppsäkring än själva FTX-aggregatet.  
* Även om strömmen till aggregatet är bruten, kan det komma upp livsfarlig spänning (230V) via styrkabeln om någon trycker på spiskåpans knappar.  
* Kontrollera alltid om det går in mer än en kabel i aggregatet eller säkerhetsbrytaren.  
* Mät extremt noga på samtliga plintar innan arbetet påbörjas, även de som ser ut att vara bara styrning.  
* Fotografera alltid inkopplingen i det gamla aggregatet innan något klipps eller lossas, ifall kunden senare får problem med spiskåpan.  
* När Alliance-styrningen ska tas ur drift måste varje enskild ledare (inklusive nolla och jord) i styrkabeln isoleras separat med Wago-klämmor.  
* Dessa Wago-klämmor ska placeras i en godkänd och dragavlastad kopplingsdosa (t.ex. kulodosa) som märks tydligt med t.ex. "Gammal styrning från köksfläkt - URKOPPLAD".

## 3. Fysisk demontering av anslutningskabel  

* Klipp ALDRIG kabeln rakt av mellan säkerhetsbrytaren och aggregatet för att lämna den hängande med Wago-klämmor.  
* Om säkerhetsbrytaren oavsiktligt slås på skapas då en livsfarlig situation med spänningsförande klämmor öppet i en miljö där personer rör sig.  
* För rätt demontering: Öppna säkerhetsbrytarens kapsling och säkerställ spänningslöshet igen på inkommande plintar.  
* Skruva därefter loss aggregatets ledare från utgående plintar inuti brytaren.  
* Lossa dragavlastningen för den utgående kabeln och dra ut kabeln helt från säkerhetsbrytaren.  
* Säkerhetsbrytaren är nu tom på lastsidan och är redo att återanvändas som matningspunkt för ett IP44-uttag till nya FLUXen.

## 4. Uppmätning och identifiering inför installation  

* För att ansluta ett vanligt vägguttag måste vi säkerställa att vi har 230V, vilket kräver att spänningen slås på tillfälligt för mätning och sedan bryts igen.  
* Enfasmätning: Mät Fas (L) mot Nolla (N) för att säkerställa 230V.  
* Mät Fas mot Skyddsjord (PE) för att säkerställa 230V.  
* Nolla mot Skyddsjord ska visa ~0V.  
* Trefasmätning: Om den gamla FTX:en matades med trefas kommer du mäta 400V mellan faserna, vilket är livsfarligt för ett uttag.  
* Du måste mäta 230V mellan en fas (t.ex. L1) och Nollan.  
* Vid trefas: Välj ut en fas, Nollan och Skyddsjorden till uttaget.  
* De andra överblivna faserna måste isoleras individuellt med Wago-klämmor och vikas undan i en dragavlastad kopplingsdosa innan uttaget.  
* Om det saknas Nolla eller Jord måste en UE kontaktas för omkopplingar i centralen.

## 5. Färgkoder och åldrad kabel  

* Lita aldrig blint på kabelfärgerna, lita bara på mätinstrumentet.  
* Gul/Grön ska vara skyddsjord, men mät alltid att den har kontakt med jordskenan i centralen.  
* Före 1970 kunde skyddsjorden vara röd.  
* Blå ska vara nolla, men i äldre 400V-system utan nollbehov var det tillåtet att använda blå som fas eller tändtråd.  
* Svart (ofta L1), brun (L2) och vit (L3) var klassiska fasfärger från 70/80-talet.  
* Kablar som legat på kalla/varma vindar tappar mjukgöraren över tid.  
* Om du böjer en åldrad kabel för snabbt eller snävt spricker isoleringen ofta hela vägen in till kopparn.  
* Använd en riktig kabelskalare i stället för skaltång för att inte skada kardelerna eller den sköra innermanteln.  
* Om isoleringen spricker måste kabeln kortas ner tills du når fräsch, flexibel isolering.  
* Räcker inte kabeln måste en godkänd skarvdosa sättas innan uttaget, eller så måste hela kabeln bytas.

## 6. Montering och idrifttagning av IP44 Aqua Stark  

* För att kapslingsklassen ska gälla måste kabelgenomföringen vara helt tät.  
* Använd rätt strypnippel/membran och låt kabelmanteln gå hela vägen in i dosan.  
* Utför alltid "rycktestet" genom att dra i varje tråd för att försäkra dig om att de sitter korrekt i sina anslutningspunkter.  
* Detta minimerar risken för varmgång och glappkontakt.  
* Avslutande kontroll: Slå på strömmen, testa uttaget och verifiera att eventuell jordfelsbrytare löser ut vid test.  
* Kolla alltid med kunden så att kunden är medveten om vad som händer.
