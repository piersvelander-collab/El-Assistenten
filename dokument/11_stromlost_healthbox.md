# **Felsökning – Strömlöst vägguttag eller Healthbox som inte startar**

*(Instruktion för chatboten: Du agerar som en lugn, analytisk och stöttande mentor. När montören inte får igång systemet är de ofta stressade. Din uppgift är att guida dem genom en logisk felsökningskedja, steg för steg. Påminn dem om att de flesta fel är enkla att fixa och beröm dem när de hittar felet!)*

## **1. Kontrollera "Källan" (Elcentralen)**

* Innan vi börjar mäta i dosor kollar vi det mest uppenbara.
* El är som vatten – om kranen i källaren är avstängd kommer inget ur duschen.
* **Säkringen:** Gå till elcentralen och kontrollera att säkringen för den aktuella gruppen inte har löst ut.
* **Jordfelsbrytaren (JFB):** Har delar av huset slocknat? En felkoppling (t.ex. en spretande kardel som rör jordtråden) kan ha fått JFB att lösa ut.
* **Huvudsäkring:** Om allt i huset är dött är det en huvudsäkring som gått.

## **2. Mät uttaget med din spänningsprovare**

* Om säkringen är till men uttaget verkar dött, måste vi bekräfta det med fakta.
* **Mät i uttaget:** Sätt mätspetsarna i uttagets hål (mellan Fas och Nolla). Din Ironside ska visa \~230 V.
* **Resultat 0 V:** Om instrumentet är dött sitter felet i inkopplingen bakom uttaget eller i en kopplingsdosa tidigare i kedjan.

## **3. De vanligaste "Novis-felen" (Bakom uttaget)**

* Om uttaget är strömlöst trots att strömmen är på i centralen, beror det oftast på något av följande:
* **Plast i klämman (Guldlock-felet):** Om du skalat för kort (< 10 mm) kan uttagets klämma ha bitit tag i plastisoleringen istället för i kopparen. Då får vi ingen elektrisk kontakt trots att tråden "sitter fast".
* **Glappkontakt i Wago:** Har en tråd lossnat i en kopplingsdosa längre bort? Kontrollera alla dina kopplingar och gör om Ryck-testet. En lös nolla eller fas bryter hela kedjan.
* **Spretande koppar:** Om du skalat för långt (> 13 mm) kan en koppartråd nudda vid fel ställe och orsaka kortslutning.

## **4. Din livlina – "Stött på patrull?"**

* Om du har gått igenom stegen ovan, mätt upp 230 V men boxen fortfarande är stendöd, eller om kopplingarna känns som ett olösligt ormbo, är det dags att ringa supporten.
* "Om du stöter på patrull och behöver hjälp med elen eller kopplingarna, ring elansvarig."

## **5. Felsökningsschema för chatbot**

|Symptom|Trolig orsak|Proffsets åtgärd|
|-|-|-|
|Helt dött uttag|Säkringen har löst ut.|Kontrollera och återställ i centralen.|
|Helt dött uttag (Säkring OK)|Avbrott i koppling (ofta plast i klämman).|Skruva loss uttaget, kontrollera skalning (10–13 mm) och gör Ryck-test.|
|Uttag OK (\~230 V), healthbox död|Dålig kontakt i stickpropp eller fel på healthbox.|Kontrollera att kontakten sitter i botten. Kolla boxens interna LED. Kontakta ansvarig för råd.|
|Jordfelsbrytaren löser ut|Kortslutning mellan Nolla och Jord.|Kontrollera att inga trådar/kardeler spretar utanför kopplingarna.|
|Krångligt eller osäkert|Komplex installation eller patrull.|Ring elansvarig!|



