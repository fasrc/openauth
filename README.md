**openauth** &mdash; *administering google-authenticator two-factor authentication*

Openauth is a recipe for system administrators looking to roll out [google-authenticator](http://code.google.com/p/google-authenticator) [TOTP](http://tools.ietf.org/html/rfc6238)-based two-factor authentication for their organization.

* Users self-provision their own secret keys using the web, requiring a username, password, and working email address (the code for this is also called [openauth](https://github.com/fasrc/openauth)).
* Secrets sit in a network filesystem share.
  Ideally this should be highly-available, but if not, we provide a mechanism for simple failover-to-cache redundancy ([hadir](https://github.com/fasrc/hadir)).
* A highly-available pair of RADIUS servers uses these secrets to handle second factor authentication for all SSH access nodes, VPN concentrators, and other protected services.  We provide a recipe for setting these up.
* In addition to the standard mobile apps (which can be configured with a QR code that the self-provisioning site displays), users have the option of using a desktop client we provide ([JAuth](https://github.com/fasrc/JAuth)).

![openauth](doc/img/openauth.png "openauth")

Self-Provisioning:

1. user contacts web server, authenticates with username + password
1. web server authenticates user, looks up email address
1. web server sends mail to user with unique link to continue (it expires a short time in the future)
1. user gets email link
1. user returns to the web server
1. web server writes to the filesystem a new secret key for the user, and presents client configuration options to the user

Usage:

<ol type="A">
<li>user connects to cluster resource (e.g. ssh head node, vpn concentrator, ...)</li>
<li>first factor auth &mdash; authenticate username + password</li>
<li>second factor auth &mdash; ask RADIUS servers to authenticate username + verification code</li>
<li>using the secret key on file, one of the RADIUS servers authenticates the user</li>
</ol>
