# SSD Image Handling Guide

This guide provides instructions to:
1. **Assemble a split disk image**
2. **Extract and mount the image**
3. **Restore the image to a disk**

## Image Details
- **Device Size**: 128GB SSD
- **OS**: Debian x64
- **Default User Credentials**:
  - Username: `user`
  - Password: `password`
- **Root Credentials**:
  - Username: `root`
  - Password: `password`
- **Auto-login**: Configured for the `user` account.
- **Startup Configuration**: Automatically starts a script in "conference mode" upon user login.

---

## Assemble the Split Image
The image is split into 100MB chunks (e.g., `image.gz_aa`, `image.gz_ab`, ...), you need to reassemble it:

```bash
cat ssd_image_* > ssd_image.img
```

---

## Extract the Image

```bash
gunzip image.img.gz
```

The result will be an uncompressed file named `image.img`.

---

## Mount the Image for Exploration

### Step 1: Identify Partitions in the Image
Use `fdisk` to list the partitions:
```bash
fdisk -l image.img
```
Example output:
```
Device         Boot  Start       End   Sectors   Size  Id Type
image.img1        2048    1050623   1048576   512M  83 Linux
image.img2     1050624  250069679 249019056  118.7G 83 Linux
```

### Step 2: Mount a Specific Partition
Calculate the offset for the desired partition by multiplying the `Start` sector by 512 (sector size). For example:
- Offset for Partition 1: `2048 * 512 = 1048576`

Mount the partition:
```bash
sudo mkdir /mnt/image_mount
sudo mount -o loop,offset=1048576 image.img /mnt/image_mount
```
The image contents will be accessible at `/mnt/image_mount`.

---

## Restore the Image to the SSD
Ensure the SSD is connected and identified (e.g., `/dev/sda`, `/dev/nvme0n1`). Replace `/dev/nvme0n1` with the correct device name in the commands below.

### Step 1: Write the Image to the SSD
```bash
sudo dd if=image.img of=/dev/nvme0n1 bs=1M status=progress
```

### Step 2: Verify the Restoration
After writing, verify the SSD:
```bash
sudo fdisk -l /dev/nvme0n1
```
Check that the partition layout matches the original image.

---

## Notes
1. **Backup Important Data**: Before restoring, ensure no important data is present on the target SSD.
2. **Run Commands with Care**: Misidentifying devices can lead to data loss.
3. **Autologin and Startup Script**: After restoration, the system will autologin to the `user` account and start the script in "conference mode" automatically.
4. **Root Access**: Use the root credentials for administrative tasks.

If you encounter any issues, double-check commands and ensure you are using the correct device identifiers.

