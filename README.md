## To Run

`bash$ make cleanall`\
`bash$ make demo`

## Introduction

A greater understanding of the standard network stack and various internet protocols has
provided an opportunity for the team of NC State University graduate students listed above to
design and develop a solution for cloud storage systems. This solution will allow enterprises to
configure any number of client hosts to automatically sync file artifacts to a configured remote
server. The team is focused on optimizing network communication between hosts to provide two
key benefits. First, to reduce network bandwidth utilization by minimizing redundant file
transfers. Second, to allow the prioritization of certain file directories; enabling specific artifacts
to be backed up with greater network priority, reducing the risk of potential client data loss
during transmission. This proposal will describe how to provide these benefits, the current
design of the solution, and how we plan to evaluate and demonstrate the finished product.

## Problem Statement

The majority of data used and stored in various enterprise environments is represented as
files. This empowers (Simple) File Transfer Protocols (S)FTP to satisfy data storage
requirements even at a large scale. The general scenario this solution pertains to is one where an
enterprise requires many clients to synchronize file system data to one or few central servers
used for backup storage. Based on one’s configuration, the central data could be shared and
updated by various clients. However, by default, each client would their own personal storage
space reserved. Regardless, enterprise data, which is generated by a multitude of employees or
systems, is managed most easily from one or few locations. In addition, we understand business
critical data will require higher priority when being synchronized. This solution will backup file
data so to avoid any loss in the event of client failures. However, because the data is copied over
a network, there will be an inherent latency from the time the data is originally created, and when
the data has been completely copied to the remote server. This delay creates a window where the
data is vulnerable to being lost. Therefore, artifacts which are deemed more critical will
minimize this window by being prioritized during network communication.
