#ifndef AWAKEN_LOGIC_H
#define AWAKEN_LOGIC_H

#include <stdint.h>
#include <wchar.h>

/* argv[0] is a path, never an activation request. */
static int HasActivateArgument(int count, wchar_t **arguments) {
    int index;
    for (index = 1; index < count; ++index) {
        if (wcscmp(arguments[index], L"--activate") == 0) return 1;
    }
    return 0;
}

/* Index order is persisted in the registry; keep existing entries stable. */
static int DurationMinutesFromSelection(int selection) {
    switch (selection) {
        case 1: return 15;
        case 2: return 30;
        case 3: return 60;
        case 4: return 120;
        case 5: return 240;
        case 6: return 480;
        default: return 0;
    }
}

static uint64_t RemainingSeconds(uint64_t milliseconds) {
    /* Round up without overflowing at UINT64_MAX. */
    return milliseconds / 1000 + (milliseconds % 1000 != 0);
}

#endif
