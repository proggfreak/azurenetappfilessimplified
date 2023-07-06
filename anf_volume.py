#!/usr/bin/python

DOCUMENTATION = '''
---
module: anf_volume
short_description: creation, update and deletion of azure netapp files volumes.
Creator: Christian Gruetzner

API Version support: (Get-AzResourceProvider -ProviderNamespace Microsoft.NetApp).ResourceTypes
Default: 2020-02-01
'''

from ansible.module_utils.basic import *
import requests
import json
import time
import math



def volume_present(data):

	if data['provider'] == "azure":
		#get first access to azure api and the correct tenant/subscription
		api_url = "https://login.microsoftonline.com/"+data['tenant']+"/oauth2/token"
		body = "grant_type=client_credentials&client_id="+data['client_id']+"&client_secret="+data['secret']+"&resource=https://management.core.windows.net"
		headers = {
			'content-type': 'application/x-www-form-urlencoded'
		}
		token = requests.get(api_url, data=body, headers=headers)
		meta = {token.status_code}
		tokeninfo = token.json()

		if token.status_code == 200:

			tokeninfo = token.json()
			
			if tokeninfo.get('token_type') == "Bearer":
				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ create the ANF account ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

				#----- get ANF account to check if existing already -----
				api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"?api-version=2020-02-01"
				headers = {
					'content-type': 'application/json',
					'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
				}
				httpreturn = requests.get(api_url, headers=headers)

				if httpreturn.status_code == 200:
					#----- do nothing if already existing! -----
					has_changed = False
					is_failed = False

				else:
					#----- create ANF account -----
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"?api-version=2020-02-01"
					body_raw = {
						'location': data['location']
					}
					body = json.dumps(body_raw)
					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.put(api_url, data=body, headers=headers)

					if httpreturn.status_code == 200:
						has_changed = False
						is_failed = False

					elif httpreturn.status_code == 201:
						#----- check if async process is complete -----
						checkasyncurl = httpreturn.headers["Azure-AsyncOperation"]
						api_url = checkasyncurl
						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.get(api_url, headers=headers)
						returndata = httpreturn.json()

						while returndata["status"] == "InProgress":
							time.sleep(10) # ask all x seconds if status changes
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()
						
						#----- check if account is in provitioningState "Succeeded" -----
						while True:
							time.sleep(5)
							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"?api-version=2020-02-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()
							if returndata["properties"]["provisioningState"] == "Succeeded":
								break

						time.sleep(10) # get secure on just waiting another 10s after creation. API sometimes says complete, but its not.

						has_changed = True
						is_failed = False

					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.status_code}
						return (is_failed, has_changed, meta)


				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ create capacity pool ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				
				#----- get capacity pool to check if existing already -----
				lowerpoolsize = 0
				poolused = 0
				poolfoundsamesize = 0
				volumefound = 0
				volumefoundsamesize = 0

				capacitypool = data['sku'].lower()
				volsizeraw = (data['volsize'] - 1) * 1024 * 1024 * 1024

				api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"?api-version=2020-02-01"
				headers = {
					'content-type': 'application/json',
					'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
				}
				httpreturn = requests.get(api_url, headers=headers)

				if httpreturn.status_code == 200:
					#----- calculate new pool size -----
					poolsize = 4398046511104
					poolinfo = httpreturn.json()
					actualpoolsize = poolinfo["properties"]["size"]
					
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes?api-version=2020-02-01"
					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.get(api_url, headers=headers)
					volinfo = httpreturn.json()
					#file = open ("/tmp/testfile.txt","w")
					#file.write (httpreturn.text)

					for i in volinfo["value"]:
						poolused = poolused + i["properties"]["usageThreshold"]
						#file.write (i["name"].split('/')[2])
						if i["name"].split('/')[2] == data['volname']:
							volumefound = 1
							volumeactualsize = i["properties"]["usageThreshold"]
					poolfreespace = actualpoolsize - poolused
					#file.close

					if volumefound == 1:
						if volumeactualsize < volsizeraw:
							neededadditionalspace = volsizeraw - volumeactualsize
							if poolfreespace < neededadditionalspace:
								reallyneeded = neededadditionalspace - poolfreespace
								poolincrease = int(math.ceil(reallyneeded / 1099511627776.0) * 1099511627776.0)
								poolsize = actualpoolsize + poolincrease
							else:
								poolsize = actualpoolsize
						elif volumeactualsize > volsizeraw:
							totalfree = poolfreespace + volumeactualsize - volsizeraw
							if totalfree >= 1099511627776:
								pooldecrease = int(math.floor(totalfree / 1099511627776.0) * 1099511627776.0)
								newpoolsize = actualpoolsize - pooldecrease
								if newpoolsize <= 4398046511104:
									lowerpoolsize = 4398046511104
								else:
									lowerpoolsize = newpoolsize
								poolsize = actualpoolsize
						else:
							poolfoundsamesize = 1
							volumefoundsamesize = 1
					else:
						if poolfreespace < volsizeraw:
							poolincrease = int(math.ceil((volsizeraw - poolfreespace) / 1099511627776.0) * 1099511627776.0)
							poolsize = actualpoolsize + poolincrease
						else:
							poolfoundsamesize = 1

				else:
					#----- if capacity pool is not existing, check if volume is larger than 4TB. If so, set vol size. Else set 4TB. -----
					if volsizeraw <= 4398046511104:
						poolsize = 4398046511104
					else:
						poolsize = volsizeraw

				#----- run only if pool not exist or needs an update -----
				if poolfoundsamesize == 0:
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"?api-version=2020-02-01"
					body_raw = {
						'location': data['location'],
						'properties': {
							'serviceLevel': data['sku'],
							'size': poolsize
						}
					}
					body = json.dumps(body_raw)
					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.put(api_url, data=body, headers=headers)

					if httpreturn.status_code == 200:
						#----- check for Succeeded status after update -----
						while True:
							time.sleep(10)
							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"?api-version=2020-02-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()
							if returndata["properties"]["provisioningState"] == "Succeeded":
								break
						
						time.sleep(10)

						has_changed = True
						is_failed = False

					elif httpreturn.status_code == 201:
						#----- check if async process is complete -----
						#file = open ("/tmp/testfile.txt","w")

						checkasyncurl = httpreturn.headers["Azure-AsyncOperation"]
						#file.write (checkasyncurl)
						api_url = checkasyncurl
						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.get(api_url, headers=headers)
						returndata = httpreturn.json()
						#file.write (json.dumps( returndata ))
						#file.write (returndata["status"])

						while returndata["status"] == "InProgress":
							time.sleep(10) # ask all x seconds if status changes
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()
							#file.write (json.dumps( returndata ))
							#file.write (returndata["status"])
						#file.close

						# #check if pool is in provitioningState "Succeeded" 
						while True:
							time.sleep(5)
							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"?api-version=2020-02-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()
							if returndata["properties"]["provisioningState"] == "Succeeded":
								break
						
						time.sleep(10) # get secure on just waiting another 10s after creation. API sometimes says complete, but its not.

						has_changed = True
						is_failed = False


					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)

		
				
				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ create volume ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				if volumefoundsamesize == 1:
					#----- do nothing if already existing and no new size but get vol mount path -----
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2020-02-01"
					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.get(api_url, headers=headers)
					returndata = httpreturn.json()
					mountip = returndata["properties"]["mountTargets"][0]["ipAddress"]

					has_changed = False
					is_failed = False
					meta = {mountip}
				
				else:
					exportpath = data['volname'].lower()
					anfsubnetid = "/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group_net']+"/providers/Microsoft.Network/virtualNetworks/"+data['virtualnetwork']+"/subnets/"+data['subnet']
					volsizeraw = (data['volsize'] - 1) * 1024 * 1024 * 1024
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2020-02-01"

					if volumefound == 1:
						#----- update volume size only instead of all parameters! -----
						body_raw = {
							'location': data['location'], # - Mandatory
							'properties': {
								'creationToken': exportpath, # - Mandatory
								'subnetId': anfsubnetid, # - Mandatory
								'usageThreshold': volsizeraw, # - Mandatory
								'protocolTypes': ['NFSv4.1'],
								'exportPolicy': {
									'rules': [
										{
											'allowedClients': '0.0.0.0/0',
											'nfsv3': 'false',
											'nfsv41': 'true',
											'ruleIndex': 1,
											'unixReadOnly': 'false',
											'unixReadWrite': 'true'
										}
									]
								}								
							}
						}
						body = json.dumps(body_raw)

					else:
						#----- create volume -----
						body_raw = {
							'location': data['location'],
							'properties': {
								'serviceLevel': data['sku'],
								'creationToken': exportpath,
								'subnetId': anfsubnetid,
								'usageThreshold': volsizeraw,
								'protocolTypes': ['NFSv4.1'],
								'exportPolicy': {
									'rules': [
										{
											'allowedClients': '0.0.0.0/0',
											'nfsv3': 'false',
											'nfsv41': 'true',
											'ruleIndex': 1,
											'unixReadOnly': 'false',
											'unixReadWrite': 'true'
										}
									]
								}
							}
						}
						body = json.dumps(body_raw)

					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}

					httpreturn = requests.put(api_url, data=body, headers=headers)

					if httpreturn.status_code == 200:
						#----- get vol mount path -----
						api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2020-02-01"
						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.get(api_url, headers=headers)
						returndata = httpreturn.json()
						mountip = returndata["properties"]["mountTargets"][0]["ipAddress"]

						has_changed = True
						is_failed = False
						meta = {mountip}

					elif httpreturn.status_code == 201:
						#----- check if async process is complete -----
						checkasyncurl = httpreturn.headers["Azure-AsyncOperation"]
						api_url = checkasyncurl
						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.get(api_url, headers=headers)
						returndata = httpreturn.json()

						while returndata["status"] == "InProgress":
							time.sleep(10) # ask all x seconds if status changes
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()

						has_changed = True
						is_failed = False

						while True:
							time.sleep(10)
							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2020-02-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()
		#					file.write("Volume Status = "+str(returndata["properties"]["provisioningState"]))
							if returndata["properties"]["provisioningState"] == "Succeeded":
								break
							elif returndata["properties"]["provisioningState"] == "Failed":
								has_changed = False
								is_failed = True
								meta = {"Volume creation failed unexpected. Please contact your automation team."}
								return (is_failed, has_changed, meta)
									
						mountip = returndata["properties"]["mountTargets"][0]["ipAddress"]
						meta = {mountip}
									
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ decrease capacity pool if needed ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				if lowerpoolsize > 0:
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"?api-version=2020-02-01"

					body_raw = {
						'location': data['location'],
						'properties': {
							'serviceLevel': data['sku'],
							'size': lowerpoolsize
						}
					}
					body = json.dumps(body_raw)

					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}

					httpreturn = requests.put(api_url, data=body, headers=headers)

					if httpreturn.status_code == 200:

						while True:
							time.sleep(5)
							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"?api-version=2020-02-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()
							if returndata["properties"]["provisioningState"] == "Succeeded":
								break
						
						time.sleep(10)

						has_changed = True
						is_failed = False
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)
			else:
				has_changed = False
				is_failed = True
				meta = {"Failed to get access token to azure! please check your credentials!"}
		else:
			has_changed = False
			is_failed = True
			tokeninfo = token.json()
			meta = {tokeninfo["error_description"]}
	else:
		has_changed = False
		is_failed = True
		meta = {"Unsupported provider"}
			
	return (is_failed, has_changed, meta)



#######################################################################################################################################################################################################
############################## ABSENT #################################################################################################################################################################



def volume_absent(data=None):

	if data['provider'] == "azure":
		#get first access to azure api and the correct tenant/subscription
		api_url = "https://login.microsoftonline.com/"+data['tenant']+"/oauth2/token"
		body = "grant_type=client_credentials&client_id="+data['client_id']+"&client_secret="+data['secret']+"&resource=https://management.core.windows.net"
		headers = {
			'content-type': 'application/x-www-form-urlencoded'
		}
		token = requests.get(api_url, data=body, headers=headers)
		meta = {token.status_code}

		if token.status_code == 200:

			tokeninfo = token.json()
			
			if tokeninfo.get('token_type') == "Bearer":

				capacitypool = data['sku'].lower()

				#----- check if volume exists -----
				#GET https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.NetApp/netAppAccounts/{accountName}/capacityPools/{poolName}/volumes/{volumeName}?api-version=2020-02-01
				api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2020-02-01"
				headers = {
					'content-type': 'application/json',
					'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
				}
				httpreturn = requests.get(api_url, headers=headers)
				if httpreturn.status_code == 200:
					#----- list all snapshots of a volume -----
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/snapshots?api-version=2020-02-01"
					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.get(api_url, headers=headers)
					returndata = httpreturn.json()

					if httpreturn.status_code == 200:
						#----- delete snapshots -----
						if len(returndata["value"]) != 0:
							for snap in returndata["value"]:
								snapname = snap["name"].split("/")[3]
								api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/snapshots/"+snapname+"?api-version=2020-02-01"
								headers = {
									'content-type': 'application/json',
									'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
								}
								httpreturn = requests.delete(api_url, headers=headers)
								#meta = {snap["id"]}
								if httpreturn.status_code == 200:
									has_changed = True
									is_failed = False
									meta = {"snap deleted"}
								elif httpreturn.status_code == 202:
									loopcount = 0
									loopmax = 12
									while True:
										loopcount += 1
										time.sleep(10)
										api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/snapshots/"+snapname+"?api-version=2020-02-01"
										headers = {
											'content-type': 'application/json',
											'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
										}
										httpreturn = requests.get(api_url, headers=headers)
										if httpreturn.status_code != 200:
											if ("not found" in httpreturn.text) or (loopcount == loopmax):
												has_changed = True
												is_failed = False
												meta = {"snap deleted async"}
												time.sleep(30)
												break
								else:
									has_changed = False
									is_failed = True
									meta = {httpreturn.text}
									return (is_failed, has_changed, meta)

						#----- delete volume -----
						api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2020-02-01"
						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.delete(api_url, headers=headers)
						if httpreturn.status_code == 202:
							loopcount = 0
							loopmax = 12
							while True:
								loopcount += 1
								time.sleep(10)
								api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2020-02-01"
								headers = {
									'content-type': 'application/json',
									'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
								}
								httpreturn = requests.get(api_url, headers=headers)
								if httpreturn.status_code != 200:
									if ("not found" in httpreturn.text) or (loopcount == loopmax):
										has_changed = True
										is_failed = False
										meta = {"vol deleted async"}
										time.sleep(60)
										break
						else:
							has_changed = False
							is_failed = True
							meta = {httpreturn.text}
							return (is_failed, has_changed, meta)
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)
				else:
					if "not found" in httpreturn.text:
						has_changed = False
						is_failed = False
						meta = {httpreturn.text}
		#				return (is_failed, has_changed, meta)
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)
				
				#----- check if more volumes are in pool -----
				api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes?api-version=2020-02-01"
				headers = {
					'content-type': 'application/json',
					'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
				}
				httpreturn = requests.get(api_url, headers=headers)
				returndata = httpreturn.json()

				if httpreturn.status_code == 200:
					if len(returndata["value"]) != 0:
						#----- decrease pool size -----
						api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"?api-version=2019-06-01"
						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.get(api_url, headers=headers)

						if httpreturn.status_code == 200:
							poolinfo = httpreturn.json()
							actualpoolsize = poolinfo["properties"]["size"]
							
							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes?api-version=2019-06-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							volinfo = httpreturn.json()

							poolused = 0
							volumefound = 0

							for i in volinfo["value"]:
								poolused = poolused + i["properties"]["usageThreshold"]
								if i["name"].split('/')[2] == data['volname']:
									volumefound = 1
									volumeactualsize = i["properties"]["usageThreshold"]
							
							poolfreespace = actualpoolsize - poolused

							if (poolfreespace > 1099511627776) and (actualpoolsize > 4398046511104):
								pooldecrease = int(math.floor(poolfreespace / 1099511627776.0) * 1099511627776.0)
								lowerpoolsize = actualpoolsize - pooldecrease
								if lowerpoolsize < 4398046511104:
									lowerpoolsize = 4398046511104

								api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"?api-version=2019-06-01"
								body_raw = {
									'location': data['location'],
									'properties': {
										'serviceLevel': data['sku'],
										'size': lowerpoolsize
									}
								}
								body = json.dumps(body_raw)
								headers = {
									'content-type': 'application/json',
									'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
								}
								httpreturn = requests.put(api_url, data=body, headers=headers)

								if (httpreturn.status_code == 200) or (httpreturn.status_code == 202):
									has_changed = True
									is_failed = False
									meta = {"capacity pool size decreased"}
									return (is_failed, has_changed, meta)
								else:
									has_changed = False
									is_failed = True
									meta = {httpreturn.text}
									return (is_failed, has_changed, meta)
						else:
							has_changed = False
							is_failed = True
							meta = {httpreturn.text}
							return (is_failed, has_changed, meta)	
					else:
						#----- delete capacity pool -----
						api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"?api-version=2020-02-01"
						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.delete(api_url, headers=headers)
						if httpreturn.status_code == 202:
							loopcount = 0
							loopmax = 12
							while True:
								loopcount += 1
								time.sleep(10)
								api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"?api-version=2020-02-01"
								headers = {
									'content-type': 'application/json',
									'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
								}
								httpreturn = requests.get(api_url, headers=headers)
								if httpreturn.status_code != 200:
									if ("not found" in httpreturn.text) or (loopcount == loopmax):
										has_changed = True
										is_failed = False
										meta = {"pool deleted async"}
										time.sleep(60)
										break
						else:
							has_changed = False
							is_failed = True
							meta = {httpreturn.text}
							return (is_failed, has_changed, meta)
				else:
					if "not found" in httpreturn.text:
						has_changed = False
						is_failed = False
						meta = {httpreturn.text}
		#				return (is_failed, has_changed, meta)
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)	

				#----- check if other capacity pools exist in account -----
				api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools?api-version=2020-02-01"
				headers = {
					'content-type': 'application/json',
					'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
				}
				httpreturn = requests.get(api_url, headers=headers)
				returndata = httpreturn.json()

				if httpreturn.status_code == 200:
					if len(returndata["value"]) == 0:
						#----- get all snapshot policies and delete them -----
						api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/snapshotPolicies?api-version=2021-10-01"
						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.get(api_url, headers=headers)
						returndata = httpreturn.json()

						for policy in returndata["value"]:
							#DELETE https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.NetApp/netAppAccounts/{accountName}/snapshotPolicies/{snapshotPolicyName}?api-version=2021-10-01
							api_url = "https://management.azure.com/"+policy["id"]+"?api-version=2021-10-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.delete(api_url, headers=headers)
							time.sleep(10)
						
						# additional wait for the next step to ensure not running into "still nested ressources"
						time.sleep(60)

						#----- delete ANF account -----
						api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"?api-version=2020-02-01"
						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.delete(api_url, headers=headers)
						if httpreturn.status_code == 202:
							loopcount = 0
							loopmax = 12
							while True:
								loopcount += 1
								time.sleep(10)
								api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"?api-version=2020-02-01"
								headers = {
									'content-type': 'application/json',
									'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
								}
								httpreturn = requests.get(api_url, headers=headers)
								if httpreturn.status_code != 200:
									if ("not found" in httpreturn.text) or (loopcount == loopmax):
										has_changed = True
										is_failed = False
										meta = {"account deleted async"}
										time.sleep(60)
										break
						else:
							has_changed = False
							is_failed = True
							meta = {httpreturn.text}
							return (is_failed, has_changed, meta)

					return (is_failed, has_changed, meta)
				else:
					if "not found" in httpreturn.text:
						has_changed = False
						is_failed = False
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)
			else:
				has_changed = False
				is_failed = True
				meta = {"Failed to get access token to azure! please check your credentials!"}
		else:
			has_changed = False
			is_failed = True
			tokeninfo = token.json()
			meta = {tokeninfo["error_description"]}
	else:
		has_changed = False
		is_failed = True
		meta = {"Unsupported provider"}
		return (is_failed, has_changed, meta)



#######################################################################################################################################################################################################
############################## OFFLINE ################################################################################################################################################################



def volume_offline(data=None):

	if data['provider'] == "azure":
		#get first access to azure api and the correct tenant/subscription
		api_url = "https://login.microsoftonline.com/"+data['tenant']+"/oauth2/token"
		body = "grant_type=client_credentials&client_id="+data['client_id']+"&client_secret="+data['secret']+"&resource=https://management.core.windows.net"
		headers = {
			'content-type': 'application/x-www-form-urlencoded'
		}
		token = requests.get(api_url, data=body, headers=headers)
		meta = {token.status_code}

		if token.status_code == 200:

			tokeninfo = token.json()
			
			if tokeninfo.get('token_type') == "Bearer":

				capacitypool = data['sku'].lower()

				#----- check if volume exists -----
				#GET https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.NetApp/netAppAccounts/{accountName}/capacityPools/{poolName}/volumes/{volumeName}?api-version=2020-02-01
				api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2020-02-01"
				headers = {
					'content-type': 'application/json',
					'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
				}
				httpreturn = requests.get(api_url, headers=headers)
				if httpreturn.status_code == 200:
					#vol exists, now check used space here
					# https://management.azure.com/subscriptions/30655b8f-5095-435e-ba1c-e25d1e997164/resourceGroups/cln01/providers/Microsoft.NetApp/netAppAccounts/cln01/capacityPools/ultra/volumes/cln01sapqcpexe/providers/Microsoft.Insights/metrics?metricnames=VolumeLogicalSize,VolumeSnapshotSize&api-version=2018-01-01"
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/providers/Microsoft.Insights/metrics?metricnames=VolumeLogicalSize,VolumeSnapshotSize&api-version=2018-01-01"
					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.get(api_url, headers=headers)
					returndata = httpreturn.json()

					volume_used = 0
					snap_used = 0
					vol_used_total = 0
					if httpreturn.status_code == 200:
						#loop through result and retun the values
						if len(returndata["value"]) != 0:
							for metric in returndata["value"]:
								#file = open ("/tmp/testfile.txt","w")
								#file.write (json.dumps( metric ))
								#file.write (metric["name"]["value"])
								
								if metric["name"]["value"] == "VolumeLogicalSize":
									numofvalues = len(metric["timeseries"][0]["data"])
									volume_used = metric["timeseries"][0]["data"][numofvalues-1]["average"]
									#file.write (metric["timeseries"][0]["data"][numofvalues-1]["timeStamp"])
								if metric["name"]["value"] == "VolumeSnapshotSize":
									numofvalues = len(metric["timeseries"][0]["data"])
									snap_used = metric["timeseries"][0]["data"][numofvalues-1]["average"]
									#file.write (metric["timeseries"][0]["data"][numofvalues-1]["timeStamp"])
								#file.close
							has_changed = True
							is_failed = False
							vol_used_total = volume_used + snap_used
							#TEST for math part below: 
							#vol_used_total = 266762854400 + 49773813760
							
							#vol_used_total = bytes. convert them to gb, set minimum 100gb and round to next 100gb step if required
							if vol_used_total <= 107374182400:
								vol_used_total = 100
							else:
								vol_used_total = int(math.ceil(vol_used_total / 1024 / 1024 / 1024 / 100.0)) * 100
							meta = {vol_used_total}
							return (is_failed, has_changed, meta)
						else:
							has_changed = False
							is_failed = True
							meta = {httpreturn.text}
							return (is_failed, has_changed, meta)
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)
				else:
					if "not found" in httpreturn.text:
						has_changed = False
						is_failed = False
						meta = {httpreturn.text}
		#				return (is_failed, has_changed, meta)
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)
			else:
				has_changed = False
				is_failed = True
				meta = {"Failed to get access token to azure! please check your credentials!"}
		else:
			has_changed = False
			is_failed = True
			tokeninfo = token.json()
			meta = {tokeninfo["error_description"]}
	else:
		has_changed = False
		is_failed = True
		meta = {"Unsupported provider"}
		return (is_failed, has_changed, meta)



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



def main():

	fields = {
		"provider": {
			"required": False, 
			"default": "azure",
			"choices": ["azure"],
			"type": "str"
		},
		"tenant": {"required": True, "type": "str"},
		"subscription_id": {"required": True, "type": "str"},
		"client_id": {"required": True, "type": "str"},
		"secret": {"required": True, "type": "str"},
		"resource_group_net": {"required": True, "type": "str"},
		"virtualnetwork": {"required": True, "type": "str"},
		"subnet": {
			"required": False,
			"default": "sto",
			"type": "str"
		},
		"resource_group": {"required": True, "type": "str"},
		"location": {
			"required": False, 
			"default": "westeurope",
			"type": "str"
		},
		"accountname": {"required": True, "type": "str"},
		"sku": {
			"required": False, 
			"default": "Standard",
			"type": "str"
		},
		"volname": {"required": True, "type": "str"},
		"volsize": {"required": True, "type": "int"},
		"state": {
			"required": False, 
			"default": "present",
			"choices": ["present", "absent", "offline"],
			"type": "str"
		},
	}

	choice_map = {
		"present": volume_present,
		"absent": volume_absent,
		"offline": volume_offline,
	}

	module = AnsibleModule(argument_spec=fields)
	is_failed, has_changed, result = choice_map.get(module.params["state"])(module.params)
	module.exit_json(failed=is_failed, changed=has_changed, msg=result)



if __name__ == '__main__':
	main()


