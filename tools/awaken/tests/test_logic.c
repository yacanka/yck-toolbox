#include <stdio.h>
#include <stdlib.h>
#include "../awaken_logic.h"

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "Failed at line %d: %s\n", __LINE__, #condition); exit(1); \
} } while (0)

int main(void) {
    int durations[] = {0, 15, 30, 60, 120, 240, 480};
    wchar_t *pathOnly[] = {L"C:\\--activate\\awaken.exe"};
    wchar_t *partial[] = {L"awaken.exe", L"--activate-later"};
    wchar_t *embedded[] = {L"awaken.exe", L"prefix--activate"};
    wchar_t *exact[] = {L"C:\\Program Files\\Awaken.exe", L"--activate"};
    wchar_t *multiple[] = {L"awaken.exe", L"--unknown", L"--activate"};
    int index;
    for (index = 0; index < 7; ++index) CHECK(DurationMinutesFromSelection(index) == durations[index]);
    CHECK(DurationMinutesFromSelection(-1) == 0);
    CHECK(DurationMinutesFromSelection(7) == 0);
    CHECK(!HasActivateArgument(0, NULL));
    CHECK(!HasActivateArgument(1, pathOnly));
    CHECK(!HasActivateArgument(2, partial));
    CHECK(!HasActivateArgument(2, embedded));
    CHECK(HasActivateArgument(2, exact));
    CHECK(HasActivateArgument(3, multiple));
    CHECK(RemainingSeconds(0) == 0);
    CHECK(RemainingSeconds(1) == 1);
    CHECK(RemainingSeconds(999) == 1);
    CHECK(RemainingSeconds(1000) == 1);
    CHECK(RemainingSeconds(1001) == 2);
    CHECK(RemainingSeconds(28800000) == 28800);
    CHECK(RemainingSeconds(UINT64_MAX) == UINT64_MAX / 1000 + 1);
    puts("Awaken logic tests passed");
    return 0;
}
