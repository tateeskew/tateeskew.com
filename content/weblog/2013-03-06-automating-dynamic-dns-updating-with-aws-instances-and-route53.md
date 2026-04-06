---
title: Automating Dynamic DNS updating with AWS Instances and Route53
date: 2013-03-06T06:11:27+00:00
aliases:
  - /2013/03/06/automating-dynamic-dns-updating-with-aws-instances-and-route53/
featured_image: /images/aws_route53_header_clouds.jpg
snap_isAutoPosted:
  - 1
snapTR:
  - |
    s:333:"a:1:{i:0;a:8:{s:4:"doTR";s:1:"1";s:12:"apTRPostType";s:1:"T";s:11:"SNAPTformat";s:7:"%TITLE%";s:10:"SNAPformat";s:97:"<p>New post at %URL%</p><p><strong>%TITLE%</strong></p><p><img src='%IMG%'/></p><p>%FULLTEXT%</p>";s:11:"isPrePosted";s:1:"1";s:8:"isPosted";s:1:"1";s:4:"pgID";i:44691686592;s:5:"pDate";s:19:"2013-03-06 06:20:45";}}";
snapEdIT:
  - 1
categories:
  - computing
tags:
  - amazon web services
  - aws
  - cloud
  - devops
  - dns
  - route53
  - systems engineering

---
**UPDATE**: This information is long out of date. With the release of the awscli toolset in pypi years ago, things have changed a bit. Also, Amazon is forcing you to VPC on new accounts (years ago now). I will not be updating this post, but maybe you can find something useful here.

<span class="largestartfont">R</span>ecently I've been building the underlying system platform for the development of our distributed application on AWS. We do a lot of clustering using [Storm][1] and [Hadoop][2], which means that we sometimes spin up hundreds of instances that may only live for a few hours during a run. Getting metrics, logs and all of those 'must-haves' centralized has been part of this build-out. When working with large amounts of machines in short-lived clusters, it becomes a real pain in the ass to use the built-in DNS/naming mechanism/scheme that AWS provides by default. Everything starts to look the same inside of your reporting/metrics/monitoring tools when working with the arbitrary names given to the instances. Hence, this article.

<!--more-->

If you are not aware, there are thousands of machine instances running in AWS and Amazon only has a limited number of IPv4 addresses in their block(s), so all of the virtual machines are provided with DHCP addresses via NAT inside Amazonâ€™s network. This means that most of the time when you reboot an instance it will come up with a new IP address/hostname, so the setup described below not only provides us with an easy to remember hostname, it also dynamically updates our Route53 DNS with the new hostname provided by Amazon. One other reason you might use the information here is that Amazon limits the number of [Elastic IPs][3] that you receive with your account (5). You can [request more][4], but with this setup and/or utilizing [Elastic Load Balancing (ELB)][5] you won't need to.

We are also going to make sure our script we use to update our DNS information uses the Name tag of the instance for the hostname. This is a great way to set hostnames automatically with configuration management or your preferred tool for provisioning. I use [salt-cloud][6] to spin up instances and it automatically sets the Name tag to the name you provide when initiating your instance. Perhaps there will be a post here about salt-cloud in the future.

It should be noted that the info below is specific to CentOS instances. With a little massaging this can easily be adapted to your distribution of choice. Let's get started.

### **First things first…Setup Route53 as your DNS Provider** {.wp-block-heading}

If you are a very large organization, you might only want to delegate a subdomain to Route53. To do that, [go here for direction][7] to make this happen.

If you are wanting Route53 to handle everything for your domain, it's super easy to set up as well. [Go here for easy instructions][7] on how to do this.

### **Setup IAM role and permissions for updating Route53** {.wp-block-heading}

We will want to set up a new user and group in [IAM][8] that will have specific permissions to update our DNS and read our Name tag. Let's create a group in IAM first. I called my group dns-admin, but feel free to name your group whatever you want as long as you can remember what the group is for. When you are creating the group, select "No Permissions" in the wizard when it asks about setting a policy. Once you have the group created you need to add two policies to it. The first policy described here is to give any user within the dns-admin group permission to read the tags associated with an instance. Remember, we are going to use the Name tag of our instance to set our hostname. The second policy will be used to give permissions to update Route53 with the correct information.

So, select the group you just created and go to the "Permissions" tab. You will see a button to "Attach a Policy". Click it and select "Custom Policy". For the policy name, I used 'describe-tags' for my first policy. In the policy document area you will want to copy and paste the text from below:

{
"Statement":[
{
"Sid":"Stmt1358183399710",
"Action":[
"ec2:DescribeTags"
],
"Effect":"Allow",
"Resource":[
"*"
]
}
]
}

Repeat the above process, but this time name your policy 'edit-dns' and copy and paste the text from below in the policy document form field. NOTE: Make sure you change the text where it says YOUR\_ZONE\_ID with the zone id for the domain you are using in Route53. To get the ID, just go to the Route53 web console, select the domain zone and you will see the Hosted Zone ID number in the right side column.

{
"Statement":[
{
"Action":[
"route53:ChangeResourceRecordSets",
"route53:GetHostedZone",
"route53:ListResourceRecordSets"
],
"Effect":"Allow",
"Resource":[
"arn:aws:route53:::hostedzone/YOUR_ZONE_ID"
]
},
{
"Action":[
"route53:ListHostedZones"
],
"Effect":"Allow",
"Resource":[
"*"
]
}
]
}

Now, let's create the user that we will add to this group. I named my user the same as my group, 'dns-admin'. You will be asked to download the credentials/keys for this user as soon as you create the user. If you've created users before, you know that this is the ONLY time you get this information, so make sure you download it and keep it safe. We will need these keys in a minute.  
Once you download your keys, add the user to the group we just created and we are done with IAM.

### **Fire up an instance** {.wp-block-heading}

Once you have Route53 and your IAM user/group set up to use with your domain, fire up and instance using your base AMI. I'm sure you already have a base AMI that you configure with an init script or perhaps configuration management tools like Salt, Puppet, or Chef. Right?

After your instance comes up we need to log into the instance and grab the tools that we will utilize in our scripts.

### **Tools we need** {.wp-block-heading}

<ul class="wp-block-list" id="linklist">
<li>
cli53 – <a href="https://github.com/barnybug/cli53">https://github.com/barnybug/cli53</a>
</li>
<li>
ec2 API Tools – <a href="http://aws.amazon.com/developertools/351">http://aws.amazon.com/developertools/351</a>
</li>
<li>
ec2-metadata – <a href="http://aws.amazon.com/code/1825">http://aws.amazon.com/code/1825</a>
</li>
</ul>

### **Install and configure cli53** {.wp-block-heading}

cli53 is a great tool that interfaces easily with the Route53 API, making it easy to do updates. The easiest way to install cli53 is to just use 'pip'. On CentOS machines, pip's executable is 'pip-python'. Other distributions just use the name 'pip'. Run the following command to check if the 'python-pip' package is installed. If it's not, the command will install it for you.

command -v pip-python > /dev/null 2>&1 || { yum install -y python-pip; }

Now, the command to install 'cli53' using pip.

pip-python install cli53

Now, let's configure the cli53 tool with our AWS keys and other settings. We will create the the file '/etc/route53/config' and enter the details there. Enter the following to create the file and set permissions correctly:

mkdir /etc/route53; chmod 700 /etc/route53; touch /etc/route53/config; chmod 600 /etc/route53/config

Paste the following in the '/etc/route52/config' file. Make sure to replace the text within the quotes for each setting with your own keys, domain/subdomain, and TTL. I use a very short TTL because sometimes instances will be initiated and shortly thereafter rebooted. Use the keys that you downloaded earlier when we created the 'dns-admin' user in IAM.

# Set access and secret key of a user that
#only has access to the following AWS objects/privileges:
#"ec2:DescribeTags"
#"route53:ChangeResourceRecordSets",
#"route53:GetHostedZone",
#"route53:ListResourceRecordSets"
#"route53:ListHostedZones"
AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID_HERE"
AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY_HERE"
ZONE="THE_NAME_OF_YOUR_DOMAIN_OR_SUBDOMAIN"
TTL="30"

### **Install and configure ec2 API Tools** {.wp-block-heading}

The ec2 API tools require Java. The application servers I use require Oracle's Java, so I bake that into my base AMI. Therefore my $JAVA\_HOME env variable is set accordingly. Just make sure that if you use the OpenJDK or JRE, that you point $JAVA\_HOME to the correct place in the config below. So, install java however you like and then continue on.

Run the following commands to install the API tools to /opt/aws

mkdir -p /opt/aws
wget -q http://s3.amazonaws.com/ec2-downloads/ec2-api-tools.zip
unzip -qq ec2-api-tools.zip
rsync -a --no-o --no-g ec2-api-tools-*/ /opt/aws/

Make sure to add '/opt/aws' to your PATH and set the following env variables. You can do so by editing or creating the file '/etc/profile.d/aws.sh' and adding the following:

export EC2_HOME=/opt/aws
for i in $EC2_HOME
do
PATH=$i/bin:$PATH
done
PATH=/opt/aws/:$PATH

Source the '/etc/profile.d/aws.sh' file to make sure the PATH is added in your current session.

source /etc/profile.d/aws.sh

Also, as mentioned above, make sure the $JAVA_HOME is set. I do this by creating the file '/etc/profile.d/java.sh' and adding the following for Oracle Java:

JAVA_HOME=/usr/java/default
export JAVA_HOME

### **Install and configure ec2-metadata** {.wp-block-heading}

The only thing we have to do to install 'ec2-metadata' is to download it from the link above, place it in '/opt/aws', and make it executable. That's it!

cd /opt/aws
wget -q http://s3.amazonaws.com/ec2metadata/ec2-metadata
chmod +x ec2-metadata

### **Create the script to update Route53 and set the hostname** {.wp-block-heading}

Next on our list is to create the script we will use that will update Route53 and set our hostname based on the Name tag of our instance. Create the file /usr/sbin/update-dns-route53 and paste the script printed below into the file. Make sure to replace the YOUR\_DOMAIN\_HERE text with the domain you are using. Also, make the file executable after saving it.

#!/bin/sh
#This script will get the Name tag of the instance from EC2 and apply it #both as a CNAME record
#in Route53 for the specified domain below and update the hostname on the #machine and in the hosts file.

# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
echo "This script must be run as root" >& 2
exit 1
fi

# Load configuration
. /etc/route53/config.sh
. /etc/profile.d/java.sh
. /etc/profile.d/aws.sh

# Export access key ID and secret for our tools
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY

# Replace this with your domain
DOMAIN=YOUR_DOMAIN_HERE

HOSTNAME=$(/opt/aws/bin/ec2-describe-tags -O $AWS_ACCESS_KEY_ID -W $AWS_SECRET_ACCESS_KEY \&lt;br>--filter "resource-type=instance" \&lt;br>--filter "resource-id=$(/opt/aws/ec2-metadata -i | cut -d ' ' -f2)" \&lt;br>--filter "key=Name" | cut -f5)

IPV4=/usr/bin/curl -s http://169.254.169.254/latest/meta-data/public-ipv4

# Set the host name&lt;br>/bin/hostname $HOSTNAME.$DOMAIN
echo $HOSTNAME.$DOMAIN > /etc/hostname

# Set host name on Red Hat variants
/bin/sed -i '/HOSTNAME/d' /etc/sysconfig/network
echo HOSTNAME=$HOSTNAME.$DOMAIN >> /etc/sysconfig/network

# Add fqdn to hosts file
/bin/cat &lt; /etc/hosts
# This file is automatically genreated by /usr/sbin/update-dns-route53 script
127.0.0.1 localhost
$IPV4 $HOSTNAME.$DOMAIN $HOSTNAME
# The following lines are desirable for IPv6 capable hosts
::1 ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
ff02::3 ip6-allhosts
EOF

# Use command line scripts to get public hostname
PUBLIC_HOSTNAME=$(/opt/aws/ec2-metadata | grep 'public-hostname:' | cut -d ' ' -f 2)

# Create a new CNAME record on Route 53, replacing the old entry if nessesary
/usr/bin/cli53 rrcreate "$ZONE" "$HOSTNAME" CNAME "$PUBLIC_HOSTNAME" --replace --ttl "$TTL"


Now that we have our script, we will want to run it at boot time every time the instance is started. To do that, let's put the following in '/etc/rc.local'

/bin/bash /usr/sbin/update-dns-route53 > /tmp/updatedns 2>&1

Notice that we are redirecting the output to '/tmp/updatedns'. I've done this so that if there is a problem with the image not updating its name, you can look in this file for errors. Keep that in mind when getting this to work.

### **Create 'delete-dns-route53' script and initscript** {.wp-block-heading}

So, we'll want to delete these entries each time the machine shuts down, so we need a delete script, too. Create a new file '/usr/sbin/delete-dns-route53' and paste the following into it. Also, make sure to make the file executable after saving it.

#!/bin/sh
# This script will delete the hostname from Route53 on shutdown of the machine
# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
echo "This script must be run as root" 1>&2
exit 1
fi

# Load configuration
. /etc/route53/config
. /etc/profile.d/java.sh
. /etc/profile.d/aws.sh

# Export access key ID and secret for our tools
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY

HOSTNAME=$(/opt/aws/bin/ec2-describe-tags -O $AWS_ACCESS_KEY_ID -W $AWS_SECRET_ACCESS_KEY \
--filter "resource-type=instance" \
--filter "resource-id=$(/opt/aws/ec2-metadata -i | cut -d ' ' -f2)" \
--filter "key=Name" | cut -f5)

# Delete the hostname from DNS on shutdown 
/usr/bin/cli53 rrdelete "$ZONE" "$HOSTNAME"

We want to make sure this delete script runs every time the machine is powered down because every single time it's powered down, could be its last and we don't want our zone to become full of obsolete entries. Create the file '/etc/init.d/removednsfromroute53' and add paste the following text in it:

#!/bin/bash
# chkconfig: 35 10 10
# description: Removed DNS entries from Route53
#

. /etc/init.d/functions
lockfile=/var/lock/subsys/removednsfromroute53

case "$1" in
start)
touch $lockfile
;;
stop)
/usr/sbin/delete-dns-route53 1> /tmp/deletedns 2>&1
rm -f $lockfile
;;
restart)
$0 stop
$0 start
;;
*)
echo "Usage: $0 {start|stop|restart|status}"
exit 1
;;
esac
exit 0

As you can see, we call the 'delete-dns-route53' script within the init script.  
Now, add it to the correct runlevels by issuing the following command:

chkconfig --add removednsfromroute53

Well, there you have it…short and sweet, right? You might now want to create a new AMI based on this instance for your new base image. Moving forward if you spin up your instances with a Name tag, the name within the tag will be set as the hostname, the host's file will be updated and a new CNAME will be created within Route53. Get DNS'ing…or something like that!

[1]: http://storm-project.net/
[2]: http://hadoop.apache.org/
[3]: http://aws.amazon.com/ec2/#features
[4]: http://aws.amazon.com/contact-us/eip_limit_request/
[5]: http://aws.amazon.com/elasticloadbalancing/
[6]: https://github.com/saltstack/salt-cloud
[7]: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/CreatingNewSubdomain.html
[8]: http://aws.amazon.com/iam/