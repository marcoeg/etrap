# Onboarding of a New Organization

Required:
- organization name
- organization id

Example:
- organization name: **Vantage**
- organization_id: **vantage**

>A master account in the NEAR blockchain is also needed. In the examples `etrap.testnet` is used. Edit `MASTER_ACCOUNT` if using the script.

See below for a script for automatic generation or follow along for manual steps.

IMPORTANT: While the platform is under development, the onboarding of a new organization is in NEAR `testnet`.

### 1. Generate the organization NEAR account

```
$ near create-account {organization_id}.testnet --masterAccount etrap.testnet --initialBalance 2
```

Example:

```
$ near create-account vantage.testnet --masterAccount etrap.testnet --initialBalance 10 --verbose

Calling testnet.create_account() to create vantage.testnet using etrap.testnet
Transaction Id B3dVE5Ahnkp8pmQjBHNiEBW4zckbAAzzSX2vsxJTnpwN
Open the explorer for more info: https://testnet.nearblocks.io/txns/B3dVE5Ahnkp8pmQjBHNiEBW4zckbAAzzSX2vsxJTnpwN
Storing credentials for account: vantage.testnet (network: testnet)
Saving key to '~/.near-credentials/testnet/vantage.testnet.json'
```
Notes:
- an account for {organization_id} may already exist
```
$ cat ~/.near-credentials/testnet/vantage.testnet.json 
{
    "account_id":"vantage.testnet",
    "public_key":"ed25519:SeYYWusZHft6yKnMwyF12LCGYXyeXvDXdW7FWKWCTY5",
    "private_key":"ed25519:yeRHHaw55jShpStEgxQjDDenagCDJEUoUUufaBfHpXenCs1bkH9MkozHw6KJaWd3Y84mT6q4xnzbMkkdAT6aoB7"
}
```
### 2. Verify account

```
$ near state {organization_id}.testnet
```

Example:
```
$ near state vantage.testnet

Account vantage.testnet
{
  amount: '2000000000000000000000000',
  block_hash: '8GtNHvGLtG9F8yRHF6dJ8zQGq8gVH8kKfF9mXjd1M2Hy',
  block_height: 202829517,
  code_hash: '11111111111111111111111111111111',
  locked: '0',
  storage_paid_at: 0,
  storage_usage: 182,
  formattedAmount: '2'
}
```

### 3. Deploy organization NEAR smart contract

```
# Clone the ETRAP NEAR smart contract  from the [repo on Github](https://github.com/marcoeg/etrap-notary). 
#
# Set the contract build directory in CONTRACT_DIR
CONTRACT_DIR={contract_dir}
```

```
$ near deploy {organization_id}.testnet $CONTRACT_DIR/etrap_contract.wasm

```
Note: use the same command for re-deploying

Example:
```
$ CONTRACT_DIR=/home/marco/Development/mglabs/etrap/near/notary/out

$ near deploy vantage.testnet $CONTRACT_DIR/etrap_contract.wasm

Deploying contract /home/marco/Development/mglabs/etrap/near/notary/out/etrap_contract.wasm in vantage.testnet
Done deploying to vantage.testnet
Transaction Id 6gBCMEE4wCkb6GmKgX5VvL7wjcYpNiwFZMz7GJ4VjckR
Open the explorer for more info: https://testnet.nearblocks.io/txns/6gBCMEE4wCkb6GmKgX5VvL7wjcYpNiwFZMz7GJ4VjckR

```
Note: the account id is the contract name as well

### 4. Initialize the contract

```
$ near call {organization_id}.testnet new \
    '{"organization_id": "{organization_id}.testnet", "organization_name": "{organization_name}", "etrap_treasury": "etrap-treasury.testnet", "etrap_fee_amount": 0.05}' \
    --accountId {organization_id}.testnet
```
Note: not needed when re-deploying

Example:
```
$ near call vantage.testnet new \
    '{"organization_id": "vantage.testnet", "organization_name": "Vantage", "etrap_treasury": "etrap-treasury.testnet", "etrap_fee_amount": 0.05}' \
    --accountId vantage.testnet

Scheduling a call: vantage.testnet.new({"organization_id": "vantage.testnet", "organization_name": "Vantage", "etrap_treasury": "etrap-treasury.testnet", "etrap_fee_amount": 0.05})
Transaction Id jcLBEL2yZxn1pC1uhnywRcUePFpjSSHpo43rXrpHeop
Open the explorer for more info: https://testnet.nearblocks.io/txns/jcLBEL2yZxn1pC1uhnywRcUePFpjSSHpo43rXrpHeop
''
```
A script to check if a transaction with the new account succeeded is in `test_tx_succeed.sh`

Example:
```
 ./test_tx_success.sh 
🚀 Sending 0 NEAR from vantage.testnet to itself...
🔍 Waiting for transaction AyyH2eB3sPKDztrmxYbuKGKjYNKANvfNCGScsNhvVcMZ to complete...
✅ Transaction succeeded

```

## Using the onboarding script

A script that executes all the steps needed for onboarding is in `onboarding_organization.sh`. 

>The [ETRAP NEAR smart contract repo](https://github.com/marcoeg/etrap-notary) needs to be cloned and accessible by the script. 

- Edit `MASTER_ACCOUNT` and `CONTRACT_DIR` before using the script.
- Parameters are the Organization Name and ID.

Example:
```
$ ./onboard_organization.sh "Lunaris" "lunaris"

🚀 Starting onboarding for: Lunaris (lunaris.testnet)
🔧 Creating NEAR account lunaris.testnet...
🔍 Waiting for account creation tx 2oBsmucrYvELpB6Y23WupLCYukZ94EFce4f9yBgGAf8V to complete...
✅ Transaction 2oBsmucrYvELpB6Y23WupLCYukZ94EFce4f9yBgGAf8V succeeded
🔍 Verifying account lunaris.testnet exists...
📦 Deploying contract to lunaris.testnet...
🔍 Waiting for deploy tx FPNnjmQUs6RZcsVTGkDNVqnYsBUMq4WUBkbhUrP442Ra to complete...
✅ Transaction FPNnjmQUs6RZcsVTGkDNVqnYsBUMq4WUBkbhUrP442Ra succeeded
⚙️ Initializing contract for Lunaris...
🔍 Waiting for init tx BAii1xEgrzy72HbKjK8LJbXa7oxK3Cur53G19MNJVBkt to complete...
✅ Transaction BAii1xEgrzy72HbKjK8LJbXa7oxK3Cur53G19MNJVBkt succeeded
🎉 Onboarding completed for Lunaris (lunaris.testnet)
📄 Full log written to ./logs/onboard_lunaris_20250625_090210.log
```

The script generates a log in ` ./logs/onboard_lunaris_20250625_090210.log` with the full output.

> The new account credentials are not listed in the console or the log file and if needed they are in the `~/.near-credentials/testnet/` directory in the file `{organization_id}.testnet.json`.

## Next step: create the docker container
Once `onboard_organization.sh` completed it must be followed by Docker container generation for deployment
to generates a complete, self-contained Docker setup that customers can deploy in their environment.

Follow the instructions in [README](./docker/README.md)


