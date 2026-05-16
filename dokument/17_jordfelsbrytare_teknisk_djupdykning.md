# Teknisk Djupdykning: Så fungerar jordfelsbrytaren (JFB)

Jordfelsbrytaren (engelska: **Residual Current Device**, RCD) är en av de absolut viktigaste skyddskomponenterna i en modern elanläggning. Medan dvärgbrytare (säkringar) skyddar anläggningen mot överlast och kortslutning, är jordfelsbrytarens primära uppgift att skydda ****människor och djur**** mot livsfarliga elchocker, samt att skydda fastigheten mot elbränder orsakade av krypströmmar.

## 1. Grundprincipen: Kirchhoffs strömlag  

Jordfelsbrytarens funktion bygger på en enkel fysikalisk lag: All ström som leds in i en felfri krets måste också ledas ut ur den.

I en vanlig enfas-grupp innebär detta att strömmen som flyter fram i **Fasledaren (L)** ska vara exakt lika stor som den ström som flyter tillbaka i **Nolledaren (N)**.

I*{Fas} = I*{Nolla}

Om dessa två strömmar inte är lika stora, betyder det att elektroner "smiter" en annan väg tillbaka till transformatorn – oftast genom jord (PE). Denna "smitande" ström kallas för ****felström**** eller ****läckström****. Det är exakt denna obalans som jordfelsbrytaren detekterar.

## 2. JFB:ns inre komponenter  

För att kunna mäta denna obalans blixtsnabbt innehåller JFB:n tre viktiga huvuddelar:

### A. Summaströmsomvandlaren (Hjärtat)  

Detta är en ringkärnetransformator. Både fasledaren (L) och nolledaren (N) dras rakt igenom denna magnetiska ring.  

* Eftersom strömmen i fasen och nollan rör sig i motsatta riktningar, skapar de var sitt magnetfält inuti ringen.  
* I en felfri anläggning tar dessa två magnetfält ut varandra helt (nettoflödet är noll).

### B. Mätspolen  

Runt ringkärnan sitter en tunn koppartråd lindad – detta är mätspolen (sekundärlindningen). Så länge magnetfälten från L och N tar ut varandra händer ingenting här.  

* Men, om ett jordfel uppstår (t.ex. 30 mA läcker genom en människa till jord), blir returströmmen i nollan 30 mA mindre än i fasen.  
* Plötsligt tar magnetfälten inte längre ut varandra. Denna obalans skapar ett växlande magnetfält i ringkärnan.  
* Magnetfältet inducerar (skapar) en elektrisk spänning i mätspolen.

### C. Utlösningsreläet (Musklerna)  

Mätspolen är kopplad till en extremt känslig elektromagnet (utlösningsrelä). När mätspolen skickar sin lilla inducerade ström till reläet, drar elektromagneten till sig en mekanisk spärr. Detta frigör en fjäderbelastad brytare som klipper både fasen och nollan med ett kraftigt "klick". Hela denna process, från att felet uppstår till att strömmen är bruten, tar normalt under 30 millisekunder.

## 3. Olika typer av jordfelsbrytare  

Det är viktigt att installera rätt typ av JFB beroende på vad som ska skyddas, eftersom modern elektronik kan störa den inre mätningen.

* **Typ AC:** Reagerar endast på ren växelström. Denna typ är numera förbjuden i nyinstallationer i Sverige eftersom den kan "förblindas" av modern elektronik.  
* **Typ A:** Den nuvarande standarden i bostäder. Den klarar vanlig växelström samt pulserande likström som kan skapas av tvättmaskiner, dimmers och LED-drivdon.  
* **Typ B:** Klarar även ren och utjämnad likström. Krävs ofta vid installation av solceller, frekvensomriktare och framför allt **elbilsladdare**. En likströmsläcka kan annars magnetisera ringkärnan så att JFB:n slutar fungera helt.

## 4. Därför är testknappen kritisk  

Varje JFB har en testknapp. När denna trycks in kopplas ett inbyggt motstånd in som skapar en konstgjord "läcka" förbi summaströmsomvandlaren.  
Mekaniken i utlösningsreläet kan med tiden bli trög om den står stilla i flera år. Genom att trycka på testknappen minst var sjätte månad "motioneras" mekaniken så att fjädern orkar lösa ut den dagen ett riktigt livsfarligt fel uppstår.

**Kom ihåg: En jordfelsbrytare skyddar mot fel till jord, men den kan aldrig skydda en person som isolerat ställer sig och håller en hand på fasen och den andra på nollan (eftersom JFB:n då tror att personen är en vanlig apparat).**
