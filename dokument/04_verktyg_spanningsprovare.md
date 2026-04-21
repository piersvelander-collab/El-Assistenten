\<SYSTEM\_INSTRUKTION\>  
Roll: Pedagogisk mentor. Betona att färger är ledtrådar, men att instrumentet ger sanningen.  
\</SYSTEM\_INSTRUKTION\>

\# Identifiera Fas, Nolla och Jord med spänningsprovare

Ironside är ditt viktigaste verktyg för att veta om en tråd sover eller är vaken. Den visar spänningsnivå (12-690V) via lysdioder.

\#\# 1\. Visuella ledtrådar (Färger)  
\* \*\*Modern standard:\*\* Fas är Brun/Svart, Nolla är Blå, Jord är Gul/Grön.  
\* \*\*Gammal standard:\*\* Fas är Svart/Vit, Nolla är Grå, Jord är Röd (Mät alltid, kan vara fas\!).

\#\# 2\. Mätmetoden (Uteslutningsmetoden)  
\* \*\*Hitta Fasen:\*\* Den tråd som tänder 230V-dioden mot båda de andra trådarna är din Fas.  
\* \*\*Särskilj Nolla och Jord:\*\* Mät från Fas till de andra. Fas mot Nolla \= 230V. Fas mot Jord \= 230V.  
\* \*\*Sista kontrollen:\*\* Nolla mot Jord ska visa 0V.

\#\# 3\. Tändtråd och Mellantrådar  
\* \*\*Tändtråd:\*\* Visar 0V när brytaren är av, hoppar till 230V när knappen trycks in.  
\* \*\*Mellantråd (Trappkoppling):\*\* Spänningen flyttar sig mellan två kablar när man slår på olika brytare.

\#\# 4\. Strukturerad data för chatbot

\*\*Mättabell med IVT2001\*\*

| Mätpunkt | Förväntat utslag | Identifiering |  
| :--- | :--- | :--- |  
| Tråd 1 – Tråd 2 | 230V lyser | En av dessa är Fas. |  
| Tråd 1 – Tråd 3 | 230V lyser | Om Tråd 1 tänder dioden i båda är den Fas. |  
| Fas – Nolla | 230V lyser | Din returväg. |  
| Fas – Jord | 230V lyser | Din säkerhetsväg. |  
| Nolla – Jord | 0V | Samma elektriska referenspunkt. |

\*\*Logik för brytare\*\*

| Typ av tråd | Status: Brytare AV | Status: Brytare PÅ | Funktion |  
| :--- | :--- | :--- | :--- |  
| Fas (L) | \~230 V | \~230 V | Matning. |  
| Tändtråd | 0 V | \~230 V | Styr lampan. |  
| Mellantråd | 0V / 230V | 0V / 230V | Trappkoppling. |

\*\*VID MINSTA OSÄKERHET KONTAKTA ELANSVARIG\*\*

