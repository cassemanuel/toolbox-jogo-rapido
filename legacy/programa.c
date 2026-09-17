#include <stdio.h>
#include <string.h>

int main(void)
{
    printf("Calculadora de tempo simples\n"
           "(programa simples, nao fazemos tempo completo)\n");

    int option = 0;
    menu();
    scanf("%d", &option);
    conversora(option);
    while (option != 0)
    {
        printf("algo mais?\n"
               "selecione alguma opcao ou, para sair, digite 0: ");
        scanf("%d", &option);
        if (option != 0)
        {
            menu();
        }
        conversora(option);
    };

    system("pause");
    return 0;
}

int menu()
{
    printf("\nMenu:\n"
           "1 - [NEW] playback speed calculator\n" // removi a soma
           "2 - converter Segundos\n"
           "3 -  // Minutos\n"
           "4 -  // Horas\n"
           "5 - Limpar a tela (extra)\n"
           "0 - Sair (close program)\n");
    return 0;
}

int conversora(int option)
{
    int hours, minutes, seconds, temp;
    switch (option)
    {
    case 1:
        printf("\nInsira A (minutos) e B (Playback speed in X.Y): ");
        float accelerator;
        scanf("%d %f", &temp, &accelerator);
        seconds = ((temp * 60) / accelerator);
        hours = (seconds / 60) / 60;
        minutes = (seconds / 60) % 60;
        seconds = seconds - (hours * 3600) - (minutes * 60);
        printf("convertendo nos temos: %d hora(s), %d minuto(s) e %d segundo(s).\n", hours, minutes, seconds);
        break;
    case 2:
        printf("\nDigite quantos segundos: ");
        scanf("%d", &seconds);
        minutes = seconds / 60;
        hours = minutes / 60;
        temp = minutes % 60;
        seconds = seconds - (hours * 3600) - (minutes * 60);
        printf("convertendo nos temos: %d minuto(s) ou %dh %dm%ds\n", minutes, hours, temp, seconds);
        break;
    case 3:
        printf("\nDigite quantos minutos: ");
        scanf("%d", &minutes);
        seconds = minutes * 60;
        hours = minutes / 60;
        minutes %= 60;
        temp = seconds - (hours * 3600) - (minutes * 60);
        printf("\nconvertendo nos temos: %d segundos ou %dh %dmin\n", seconds, hours, minutes);
        break;
    case 4:
        printf("\nDigite quantas horas: ");
        scanf("%d", &hours);
        seconds = hours * 3600;
        minutes = hours * 60;
        printf("convertendo nos temos: %d segundos ou %d minutos.\n", seconds, minutes);
        break;
    case 5:
        system("cls");
        printf("Clean now!!!\n\n");
        menu();
        break;
    case 0:
        printf("\nMuito obrigado por utilizar os servicos.\n\n");
        printf("VASCO\n");
        printf("=  ========================  =\n"
               "==  ======================  ==\n"
               "===   ==================   ===\n"
               "=====   ==============   =====\n"
               "======    ==========   =======\n"
               "========   ========   ========\n"
               "==============================\n"
               "==============================\n"
               "========   ========   ========\n"
               "======    ==========   =======\n"
               "=====   ==============   =====\n"
               "===   ==================   ===\n"
               "==  ======================  ==\n"
               "=  ========================  =\n\n");
        printf("aperte uma tecla...\n");
        getchar();
        break;
    default:
        printf("wrong option. Try again!");
        break;
    }
    printf("\n");
    return 0;
}