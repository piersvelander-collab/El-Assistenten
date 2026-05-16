# Hur fungerar en jordfelsbrytare? (Och varför löser den ut utan säkring?)

En jordfelsbrytare (JFB) är en billig livförsäkring som övervakar att all ström som går ut i dina apparater också kommer tillbaka samma väg.

## 1. Grundprincipen: Balansgången  

Tänk på jordfelsbrytaren som en extremt noggrann våg.  

* Den mäter strömmen som går ut genom **Fasen (L)**.  
* Den mäter strömmen som kommer tillbaka genom **Nollan (N)**.

I en felfri krets ska dessa vara exakt lika stora. Om vågen tippar över (oftast mer än 30 mA skillnad), bryter den strömmen på bråkdelen av en sekund. Skillnaden uppstår för att strömmen har hittat en "tjuvväg" till jord, till exempel genom ett trasigt värmeelement eller en människa.

## 2. Mysteriet: Varför löser den ut när säkringen är borta?  

Detta är en vanlig syn vid felsökning. Du skruvar ur säkringen till en misstänkt lampa utomhus, men JFB:n fortsätter att lösa ut. Varför?

### Svaret är "Nolla-Jord-fel"  

När du skruvar ur en säkring bryter du bara ****Fasen (L)****. Men ****Nollan (N)**** är fortfarande ihopkopplad med alla andra nollor i hela huset via nollskenan i elcentralen.

Om det finns en skada på kabeln så att ****Nollan (N)**** kommer i kontakt med ****Jorden (PE)****, uppstår ett fel:  

1. Ström kommer från **andra** apparater i huset (t.ex. kylskåpet på en annan säkring).  
2. Denna returström ska normalt gå tillbaka genom huvudnollan.  
3. Men eftersom din trasiga krets har kontakt mellan nolla och jord, "smiter" en liten del av grannkretsarnas returström ut i jorden via den trasiga kabeln.  
4. Jordfelsbrytaren ser att det saknas ström i returen för huset totalt sett – och klick! Den löser ut.

## 3. Hur hittar man felet?  

Vid ett nolla-jord-fel räcker det inte att slå av säkringar. Man måste ofta koppla bort noll-ledaren fysiskt för den krets man misstänker, eller använda en isolationstestare (megger) för att mäta mellan nolla och jord.
