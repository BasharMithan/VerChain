import csv
import tempfile
import time
from pathlib import Path
from statistics import mean
from typing import Callable, Any
from dataclasses import dataclass, asdict

from services.ledger import Ledger
from utils.blocks.blockManager import BlockManager
from validation.chain_validation import ChainValidation
from models import User, Credential, Authority, CHID, Block
from utils.utility_function import getProjectVersion



@dataclass
class InsertTime:
    blocks: int
    averageInsertTime: float
    totalInsertTime: float

@dataclass
class LookupTime:
    users: int
    existingUsersCount: int
    nonExistingUsersCount: int

    timeCostPerUserFind: float
    averageLookupTime: float
    totalLookupTime: float


@dataclass
class ChainValidationTime:
    blocksInChain: int
    ValidationCost: float
    averageValidationTime: float


@dataclass
class PerformanceResults:
    version: str
    Insertion: InsertTime
    Lookup: LookupTime
    validation: ChainValidationTime


def flattenDict(dictionay: dict[str, Any], parentKey: str = "") -> dict[str, Any]:
    """Recursively flattens a nested dictionary using dot notation."""
    items: list[tuple[str, Any]] = []
    for k, v in dictionay.items():
        new_key = f"{parentKey}.{k}" if parentKey else k
        if isinstance(v, dict):
            items.extend(flattenDict(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)




def singleTimeCall(function: Callable, *arguments, warmup: bool = True) -> tuple[float, Any]:
    """Call `function(*arguments)` once and return (elapsed_seconds, return_value).

    If `warmup` is True, the function will be called `warm_calls` times before
    measuring to mitigate first-call I/O/cache effects. This is opt-in because
    warm-up may have side-effects for mutating functions (e.g. inserts).
    """
    # support optional keyword-only warmup params via kwargs at end
  
    warmCalls: int = 5
    # detect if warmup/warmCalls passed as keyword in last positional slot
    if warmup:

        for _ in range(warmCalls):
            try:
                function(*arguments)
            except Exception:
                # ignore warmup exceptions; warmup is best-effort
                pass

    started: float = time.perf_counter()
    functionReturnValue: Any = function(*arguments)
    return time.perf_counter() - started, functionReturnValue





class Performance:
    def __init__(self, tempFilePath: Path) -> None:
        self.ledger: Ledger = Ledger(tempFilePath)
        self.blockManager = BlockManager(self.ledger, set())



    def test(self) -> None:
        ...



    def calculateLedgerInitTime(self, ledgerClass: Ledger, tempFilePath: Path) -> tuple[float, Ledger]:
        timeCosted, ledger = singleTimeCall(ledgerClass, tempFilePath) # type: ignore
        return timeCosted, ledger



    def calculateLookupTime(
            self, count: int, saved: set[User], unsaved: set[User]) -> LookupTime:
    
        savedUsers: list[User] = list(saved)
        unsavedUsers: list[User] = list(unsaved)


        # existing users total and average
        started: float = time.perf_counter()
        for user in savedUsers:
            self.ledger.findUser(
                nationalNumber=user.nationalNumber, username=user.name)
        existingUsersTotalTime: float = time.perf_counter() - started

        # non-existing users total and average
        started = time.perf_counter()
        for user in unsavedUsers:
            self.ledger.findUser(nationalNumber=user.nationalNumber, username=user.name)
        nonExistingUsersTotalTime: float = time.perf_counter() - started

        total_lookup_time = existingUsersTotalTime + nonExistingUsersTotalTime
        total_lookups = len(saved) + len(unsavedUsers)

        return LookupTime(
            users=count,
            existingUsersCount=len(saved),
            nonExistingUsersCount=len(unsaved),
            timeCostPerUserFind=total_lookup_time / total_lookups if total_lookups else 0.0,
            averageLookupTime=total_lookup_time / total_lookups if total_lookups else 0.0,
            totalLookupTime=total_lookup_time,
        )



    def calculateBlockInsertTime(self, count: int, savedUsers: set[User]) -> tuple[InsertTime, list[dict[str, Any]]]:
        """Inserts `count - 1` blocks (genesis is block 0) onto THIS instance's
        ledger. Call this on a freshly-constructed Performance instance per
        test size, or the chain length will keep accumulating across calls
        and no longer match `count`."""
 
        insertTimes: list[float] = []
        users: list[User] = list(savedUsers)

        for i in range(count):
            user = users[i]
            auth = Authority(name=f"Auth-{count + i}", businessID=200000 + i)
            doc = Credential(image="", documentID=300000 + i)
            chid = CHID(user=user, issuer=auth, credential=doc)
            block = Block(data=chid)
 
            timeCostedPerInsert, _ = singleTimeCall(self.blockManager.registerBlock, block, warmup=False)
            insertTimes.append(timeCostedPerInsert)
 
        total = sum(insertTimes)
        avg = mean(insertTimes) if insertTimes else 0.0
 
        return InsertTime(
            blocks=count,
            averageInsertTime=avg,
            totalInsertTime=total,
        ), self.ledger.blocks



    def calculateChainValidation(self, chain: list[dict[str, Any]]) -> ChainValidationTime:
        """Caclulates the time needed for the `ChainValidation` to validate a chain with N blocks, and the time for T chains.
        Args:
            blocks (`list[Block]`): The number of blocks each chain will contain.
            chains (`int`): How many chains to test.
        """

        cv: ChainValidation = ChainValidation(chain=chain)

        timeCosted, _ = singleTimeCall(cv.validate, warmup=False)

        return ChainValidationTime(
            blocksInChain=len(chain) - 1, # Genesis block is auto generated so added blocks = len(chain) - 1.
            ValidationCost=timeCosted,
            averageValidationTime=timeCosted / len(chain)
        )



    @staticmethod
    def createUsers(count: int, saved: set[User], unsaved: set[User]) -> tuple[set[User], set[User]]:
        """Creates (count) N users to be saved in the chain,
        and (count) N users, but dosen't save them. 
        Args:
            count (`int`): Count of users to create.
        Returns:
            `tuple[list[User], list[User]]`: A tuple that contains saved users, and unsaved users.
        """


        for index in range(count):
            user: User = User(name=f"saved-user-{index}", nationalNumber=index, phone=index, age=20, email=f"{index}@email.com", birth="")
            saved.add(user)

        for index in range(count):
            user: User = User(name=f"unsaved-user-{index}", nationalNumber=index, phone=index, age=20, email=f"{index}@email.com", birth="")
            unsaved.add(user)

        result = (saved, unsaved)
        return result
    


    @staticmethod
    def saveResults(results: list[PerformanceResults], version: str, filename: str = "Performance-Resutls.csv") -> None:
        """
        Saves the performace test benchmarks in a CSV file associated with the last commit.

        Args:
        results (`PerformanceResult`): The object that will be saveed in the CSV file.).
        file (`str`): The CSV file to write the results to.
        version (`str`): The curent project's version to associate it with the report.
        
        """

        if not results: return

        # Renaming the CSV file to let it reference the version
        file: str = f"{version}-" + filename

        # Convert dataclasses to dicts and flatten them with dot notation
        flattenData = [flattenDict(asdict(item)) for item in results]
        fieldnames = list(flattenData[0].keys())

        with open(file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattenData)



    @staticmethod
    def displayPerformance(results: PerformanceResults) -> None:
        """Prints the results after each iteration in the main loop.

        Args:
            results (`PerformanceResults`): The results for the iteration with a count = N.
        """
        print(f"""Performance Test (count={results.Insertion.blocks}):\nBlock build + insertion: {results.Insertion}\nLookup: {results.Lookup}\nValidation: {results.validation}""")
        

    


if __name__ == "__main__":

    baseDir: Path = Path(tempfile.mkdtemp(prefix="VerChain-performance-"))

    tests:      list[int] = [10, 50, 100, 250, 500, 100, 2000]

    saved:      set [User] = set()
    unsaved:    set [User] = set()
    results:    list[PerformanceResults] = []

    for count in tests:
        tempFilePath = baseDir / f".performance-test-ledger-{count}.json"

        savedUsers, unsavedUsers        = Performance.createUsers(count, saved=saved, unsaved=unsaved)

        performance: Performance        = Performance(tempFilePath)

        insertion,  chain               = performance.calculateBlockInsertTime(count, savedUsers=savedUsers)
        lookup:     LookupTime          = performance.calculateLookupTime(count, saved=savedUsers, unsaved=unsavedUsers)
        validation: ChainValidationTime = performance.calculateChainValidation(chain=chain)

        currentTestResult = PerformanceResults(version=getProjectVersion(), Insertion=insertion,Lookup=lookup,validation=validation)
        results.append(currentTestResult)
        Performance.displayPerformance(currentTestResult)

    Performance.saveResults(results=results, version=getProjectVersion())
    